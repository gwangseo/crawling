"""
기존 DB 상품에 대한 AI 재분석 스크립트

사용법:
  python scripts/reanalyze_ai.py              # AI 분석 없는 상품만 20개
  python scripts/reanalyze_ai.py 50           # AI 분석 없는 상품 50개
  python scripts/reanalyze_ai.py 10 --force   # 전체 상품 10개 (기존 분석 덮어씌우기)
"""
import os
import sys
import tempfile

import requests
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import text

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()


def download_image(url: str, save_path: str) -> bool:
    """Drive URL에서 이미지를 다운로드. 성공 시 True 반환."""
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
        logger.warning(f"다운로드 실패 (status {resp.status_code}): {url}")
        return False
    except Exception as e:
        logger.warning(f"다운로드 오류: {url} — {e}")
        return False


def reanalyze_products(limit: int = 20, force: bool = False) -> None:
    """
    force=False: product_layouts가 없는 상품만 분석 (첫 AI 분석)
    force=True : 기존 분석 데이터를 삭제하고 전체 재분석 (덮어씌우기)
    """
    from database.session import SessionLocal
    from database import crud
    from ai.layout_tagger import process_product_tagging, extract_keywords_from_text

    db = SessionLocal()

    try:
        if force:
            sql = text("""
                SELECT p.id::text, p.brand, p.name
                FROM products p
                ORDER BY p.created_at DESC
                LIMIT :limit
            """)
            logger.info(f"[재분석] 전체 상품 최대 {limit}개 (기존 데이터 덮어씌우기)")
        else:
            sql = text("""
                SELECT p.id::text, p.brand, p.name
                FROM products p
                WHERE NOT EXISTS (
                    SELECT 1 FROM product_layouts pl WHERE pl.product_id = p.id
                )
                ORDER BY p.created_at DESC
                LIMIT :limit
            """)
            logger.info(f"[재분석] AI 미분석 상품 최대 {limit}개")

        products = db.execute(sql, {"limit": limit}).mappings().all()
        logger.info(f"대상 상품: {len(products)}개")

        for idx, product in enumerate(products, 1):
            product_id = product["id"]
            product_label = f"{product['brand']} - {product['name']}"
            logger.info(f"[{idx}/{len(products)}] {product_label}")

            # 에셋 URL 조회
            asset_sql = text("""
                SELECT drive_url FROM assets
                WHERE product_id = CAST(:pid AS uuid)
                  AND asset_type = 'detail_image'
                  AND drive_url IS NOT NULL
                ORDER BY created_at
                LIMIT 8
            """)
            assets = db.execute(asset_sql, {"pid": product_id}).mappings().all()

            if not assets:
                logger.warning(f"  에셋 없음, 건너뜀")
                continue

            # 이미지 임시 다운로드
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_paths = []
                for i, asset in enumerate(assets):
                    save_path = os.path.join(tmp_dir, f"detail_{i:03d}.jpg")
                    if download_image(asset["drive_url"], save_path):
                        local_paths.append(save_path)

                if not local_paths:
                    logger.warning(f"  다운로드된 이미지 없음, 건너뜀")
                    continue

                logger.info(f"  {len(local_paths)}장 다운로드 완료 → Gemini 분석 시작")

                # 기존 AI 데이터 삭제 (force 여부와 관계없이 덮어쓰기 보장)
                crud.delete_product_ai_data(db, product_id)

                # 레이아웃 분석
                process_product_tagging(product_id, local_paths, db)

                # 텍스트 키워드 추출 (제품명 + 브랜드로라도 추출)
                ai_keywords = extract_keywords_from_text(
                    product_name=product["name"],
                    brand=product["brand"],
                    description="",
                    hashtags=[],
                )
                if ai_keywords:
                    crud.create_tags(db, product_id, ai_keywords)

            # 세션 갱신 (긴 작업 중 연결 유지)
            db.close()
            db = SessionLocal()

        logger.info("=" * 50)
        logger.info(f"AI 재분석 완료: {len(products)}개 처리")

    finally:
        db.close()


if __name__ == "__main__":
    _limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    _force = "--force" in sys.argv
    reanalyze_products(limit=_limit, force=_force)
