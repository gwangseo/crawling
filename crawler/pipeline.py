"""
메인 크롤링 파이프라인
URL 수집 → 상세 파싱 → 에셋 다운로드 → Drive 업로드 → DB 저장
"""
import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from loguru import logger
from playwright.async_api import async_playwright

from crawler.oliveyoung import collect_all_categories
from crawler.product_detail import parse_product_detail, download_asset
from crawler.anti_bot import get_browser_launch_args, get_context_options, apply_stealth_scripts, async_sleep_random
from storage.drive_utils import upload_product_assets
from database.session import SessionLocal
from database.models import CategoryEnum
from database import crud


SLEEP_MIN = float(os.getenv("CRAWL_SLEEP_MIN", "3.5"))
SLEEP_MAX = float(os.getenv("CRAWL_SLEEP_MAX", "8.2"))


def _map_category_enum(category_str: str) -> CategoryEnum:
    mapping = {
        "skincare": CategoryEnum.skincare,
        "mask_pack": CategoryEnum.mask_pack,
        "cleansing": CategoryEnum.cleansing,
        "sun_care": CategoryEnum.sun_care,
        "makeup": CategoryEnum.makeup,
        "nail": CategoryEnum.nail,
        "mens": CategoryEnum.mens,
        "hair_care": CategoryEnum.hair_care,
        "body_care": CategoryEnum.body_care,
        "etc": CategoryEnum.etc,
    }
    return mapping.get(category_str, CategoryEnum.etc)


async def process_single_product(page, product_meta: dict, db, tmp_dir: str) -> dict:
    """
    단일 상품 처리:
    1. DB 중복 확인
    2. 신규: 상세 파싱 + 에셋 다운로드 + Drive 업로드 + DB INSERT
    3. 기존: product_metrics만 UPDATE
    반환: {"status": "new" | "updated" | "skipped" | "error"}
    """
    oliveyoung_id = product_meta["oliveyoung_id"]
    product_url = product_meta["url"]
    category_str = product_meta["category"]
    category_name = product_meta["category_name"]

    existing = crud.get_product_by_oliveyoung_id(db, oliveyoung_id)

    # --- 기존 상품: 지표만 업데이트 ---
    if existing:
        try:
            detail = await parse_product_detail(page, product_url)
            if detail:
                crud.upsert_product_metric(
                    db, existing.id,
                    likes=detail.get("likes_count", 0),
                    reviews=detail.get("review_count", 0),
                    rating=detail.get("rating"),
                )
                logger.info(f"[업데이트] {existing.brand} - {existing.name} 지표 갱신 완료")
                return {"status": "updated"}
        except Exception as e:
            logger.error(f"[업데이트 실패] {oliveyoung_id}: {e}")
            return {"status": "error"}
        return {"status": "updated"}

    # --- 신규 상품: 전체 수집 ---
    detail = await parse_product_detail(page, product_url)
    if not detail:
        return {"status": "error"}

    # 1. 상품 정보 DB 저장
    product = crud.create_product(db, {
        "oliveyoung_id": oliveyoung_id,
        "brand": detail.get("brand", "알 수 없음"),
        "name": detail.get("name", "알 수 없음"),
        "category": _map_category_enum(category_str),
        "original_price": detail.get("original_price"),
        "discount_price": detail.get("discount_price"),
        "product_url": product_url,
    })

    # 2. 지표 저장
    crud.upsert_product_metric(
        db, product.id,
        likes=detail.get("likes_count", 0),
        reviews=detail.get("review_count", 0),
        rating=detail.get("rating"),
    )

    # 3. 키워드 저장
    if detail.get("keywords"):
        crud.create_tags(db, product.id, detail["keywords"])

    # 4. 에셋 다운로드 및 Drive 업로드
    assets_to_upload = []
    product_tmp_dir = os.path.join(tmp_dir, oliveyoung_id)

    # 썸네일
    for i, url in enumerate(detail.get("thumbnail_urls", [])[:3]):
        ext = _get_extension(url)
        filename = f"thumbnail_{i+1:02d}{ext}"
        local_path = await download_asset(url, product_tmp_dir, filename)
        if local_path:
            assets_to_upload.append({"local_path": local_path, "asset_type": "thumbnail", "filename": filename})

    # 상세 이미지
    for i, url in enumerate(detail.get("detail_image_urls", [])[:20]):
        ext = _get_extension(url)
        filename = f"detail_{i+1:03d}{ext}"
        local_path = await download_asset(url, product_tmp_dir, filename)
        if local_path:
            assets_to_upload.append({"local_path": local_path, "asset_type": "detail_image", "filename": filename})

    # GIF
    for i, url in enumerate(detail.get("gif_urls", [])[:10]):
        filename = f"animation_{i+1:02d}.gif"
        local_path = await download_asset(url, product_tmp_dir, filename)
        if local_path:
            assets_to_upload.append({"local_path": local_path, "asset_type": "gif", "filename": filename})

    # 영상 링크만 저장 (MP4는 용량이 크므로 URL만 기록)
    for i, url in enumerate(detail.get("video_urls", [])[:3]):
        crud.create_asset(db, product.id, {
            "asset_type": "video",
            "drive_file_id": None,
            "drive_url": url,
            "original_filename": f"video_{i+1:02d}",
        })

    # 5. Drive 업로드 (실패 시 URL만 DB에 저장하고 계속 진행)
    if assets_to_upload:
        try:
            uploaded = upload_product_assets(
                category=category_name,
                brand=detail.get("brand", "알 수 없음"),
                product_name=detail.get("name", oliveyoung_id),
                assets=assets_to_upload,
            )
            for asset_info in uploaded:
                crud.create_asset(db, product.id, {
                    "asset_type": asset_info["asset_type"],
                    "drive_file_id": asset_info["file_id"],
                    "drive_url": asset_info["drive_url"],
                    "original_filename": asset_info["original_filename"],
                })
        except Exception as drive_err:
            logger.warning(f"[Drive] 업로드 실패, 원본 URL만 저장: {drive_err}")
            # Drive 실패 시 원본 이미지 URL을 직접 DB에 저장
            for i, url in enumerate(detail.get("thumbnail_urls", [])[:3]):
                crud.create_asset(db, product.id, {
                    "asset_type": "thumbnail",
                    "drive_file_id": None,
                    "drive_url": url,
                    "original_filename": f"thumbnail_{i+1:02d}",
                })
            for i, url in enumerate(detail.get("detail_image_urls", [])[:20]):
                crud.create_asset(db, product.id, {
                    "asset_type": "detail_image",
                    "drive_file_id": None,
                    "drive_url": url,
                    "original_filename": f"detail_{i+1:03d}",
                })

    return {"status": "new"}


def _get_extension(url: str) -> str:
    path = url.split("?")[0]
    ext = Path(path).suffix.lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else ".jpg"


async def run_crawling_pipeline():
    """
    전체 크롤링 파이프라인 실행
    매주 금요일 18:00 APScheduler에 의해 호출됨
    """
    logger.info("=" * 60)
    logger.info("크롤링 파이프라인 시작")
    logger.info("=" * 60)

    stats = {"new": 0, "updated": 0, "skipped": 0, "error": 0}

    # Step 1: 전체 카테고리 상품 URL 수집
    product_list = await collect_all_categories()
    logger.info(f"수집 대상: 총 {len(product_list)}개 상품")

    # Step 2: 각 상품 상세 파싱 + 저장
    with tempfile.TemporaryDirectory() as tmp_dir:
        async with async_playwright() as p:
            browser = await p.chromium.launch(**get_browser_launch_args())
            context = await browser.new_context(**get_context_options())
            page = await context.new_page()
            await apply_stealth_scripts(page)

            for i, product_meta in enumerate(product_list):
                logger.info(f"[{i+1}/{len(product_list)}] {product_meta['category_name']} - {product_meta['oliveyoung_id']}")
                # DB 세션을 상품마다 새로 열어 Supabase idle timeout 방지
                db = SessionLocal()
                try:
                    result = await process_single_product(page, product_meta, db, tmp_dir)
                    stats[result["status"]] = stats.get(result["status"], 0) + 1
                except Exception as e:
                    logger.error(f"[파이프라인] 상품 처리 오류 ({product_meta['oliveyoung_id']}): {e}")
                    stats["error"] = stats.get("error", 0) + 1
                finally:
                    db.close()

                # 상품 간 랜덤 대기
                await async_sleep_random(SLEEP_MIN, SLEEP_MAX)

            await browser.close()

    logger.info("=" * 60)
    logger.info(f"크롤링 완료 - 신규:{stats['new']} | 업데이트:{stats['updated']} | 오류:{stats['error']}")
    logger.info("=" * 60)
    return stats
