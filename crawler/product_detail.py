"""
올리브영 상품 상세 페이지 파싱 모듈 (React/Next.js 기반 신버전 대응)

핵심 전략:
- 브랜드명·상품명·가격: <meta property="eg:*"> 태그에서 추출 (UI 변경과 무관, 안정적)
- 찜 수·리뷰 수: JS 렌더링 후 [class*='like'], [class*='review'] 에서 추출
- 이미지: swiper-slide img 및 detail 영역 img 추출
"""
import re
import os
import asyncio
import httpx
from pathlib import Path
from typing import Optional
from loguru import logger
from playwright.async_api import Page

from crawler.anti_bot import apply_stealth_scripts, async_sleep_random

IMAGE_CDN = "https://image.oliveyoung.co.kr/cfimages/cf-goods/uploads/images/thumbnails/"


async def parse_product_detail(page: Page, product_url: str) -> Optional[dict]:
    """
    상품 상세 페이지에서 전체 데이터 추출
    """
    try:
        await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3.0)

        title = await page.title()
        if not title or "올리브영" not in title:
            raise Exception(f"상품 페이지 로드 실패 (title: {title})")

        result = {}

        # ── 1. 메타 태그에서 핵심 데이터 추출 (안정적, UI 변경 무관) ──
        meta_data = await page.evaluate("""
            () => {
                const get = (prop) => {
                    const el = document.querySelector(`meta[property="${prop}"]`);
                    return el ? el.getAttribute('content') : '';
                };
                return {
                    name:           get('eg:itemName'),
                    brand:          get('eg:brandName'),
                    original_price: get('eg:originalPrice'),
                    sale_price:     get('eg:salePrice'),
                    image_path:     get('eg:itemImage'),
                    item_id:        get('eg:itemId'),
                };
            }
        """)

        result["name"] = meta_data.get("name", "")
        result["brand"] = meta_data.get("brand", "")
        result["original_price"] = _safe_int(meta_data.get("original_price"))
        result["discount_price"] = _safe_int(meta_data.get("sale_price"))

        # 썸네일 URL 구성 (메타 태그의 eg:itemImage는 CDN 상대 경로)
        image_path = meta_data.get("image_path", "")
        if image_path:
            thumbnail_url = IMAGE_CDN + image_path.split("?")[0]
            result["thumbnail_urls"] = [thumbnail_url]
        else:
            result["thumbnail_urls"] = []

        # ── 2. JS 렌더링 데이터: 찜 수 / 리뷰 수 ──
        await asyncio.sleep(1.5)

        result["likes_count"] = await _extract_likes(page)
        result["review_count"], result["rating"] = await _extract_review_info(page)

        # ── 3. 이미지: swiper 슬라이더 + 상세 영역 ──
        detail_imgs, gif_urls = await _extract_detail_images(page)
        result["detail_image_urls"] = detail_imgs
        result["gif_urls"] = gif_urls
        result["video_urls"] = await _extract_video_urls(page)

        # ── 4. 키워드 ──
        result["keywords"] = await _extract_keywords(page)
        result["description_text"] = ""

        logger.info(
            f"[파싱 완료] {result.get('brand')} - {result.get('name', '')[:30]} "
            f"(찜:{result['likes_count']}, 리뷰:{result['review_count']}, "
            f"썸네일:{len(result['thumbnail_urls'])}장, "
            f"상세:{len(result['detail_image_urls'])}장, "
            f"GIF:{len(result['gif_urls'])}개)"
        )
        return result

    except Exception as e:
        logger.error(f"[파싱 실패] {product_url}: {e}")
        return None


def _is_product_image(url: str) -> bool:
    """UI 아이콘/정적 에셋을 제외하고 실제 상품 이미지 URL만 허용"""
    if not url:
        return False
    # 올리브영 상품 이미지 CDN만 허용
    allowed_hosts = ("image.oliveyoung.co.kr",)
    return any(host in url for host in allowed_hosts)


def _safe_int(value: str) -> Optional[int]:
    if not value:
        return None
    cleaned = re.sub(r"[^\d]", "", str(value))
    return int(cleaned) if cleaned else None


async def _extract_likes(page: Page) -> int:
    """찜 수 추출 - 올리브영은 찜 수를 공개하지 않는 경우 0 반환"""
    try:
        count = await page.evaluate("""
            () => {
                const selectors = [
                    '[class*="wish-count"]', '[class*="WishCount"]',
                    '[class*="like-count"]', '[class*="LikeCount"]',
                    '[class*="like"]', '[class*="wish"]', '[class*="Like"]',
                ];
                for (const sel of selectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        const text = el.innerText.trim();
                        const match = text.match(/^(\\d[\\d,]*)$/);
                        if (match) return parseInt(match[1].replace(/,/g, ''));
                    }
                }
                return 0;
            }
        """)
        return count or 0
    except Exception:
        return 0


async def _extract_review_info(page: Page) -> tuple[int, Optional[float]]:
    """리뷰 수와 평점 추출
    - 리뷰 수: GoodsDetailTabs_review-count 또는 [class*='review'] 숫자 텍스트
    - 평점: [class*='rating'] 또는 [class*='score'] 소수점 텍스트
    """
    try:
        info = await page.evaluate("""
            () => {
                let count = 0;
                let rating = null;

                // 리뷰 수: review-count 클래스 우선, 그 다음 일반 review 클래스
                const reviewSelectors = [
                    '[class*="review-count"]', '[class*="ReviewCount"]',
                    '[class*="review"]', '[class*="Review"]',
                ];
                for (const sel of reviewSelectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        const text = el.innerText.trim();
                        const match = text.match(/^([\\d,]+)$/);
                        if (match) {
                            const n = parseInt(match[1].replace(/,/g, ''));
                            if (n > count) count = n;
                        }
                    }
                    if (count > 0) break;
                }

                // 평점: 4.8 형태
                const ratingSelectors = [
                    '[class*="rating"]', '[class*="Rating"]',
                    '[class*="score"]', '[class*="Score"]',
                    '[class*="star"]', '[class*="Star"]',
                ];
                for (const sel of ratingSelectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        const text = el.innerText.trim();
                        const match = text.match(/^([0-9]\\.[0-9]{1,2})$/);
                        if (match) {
                            rating = parseFloat(match[1]);
                            break;
                        }
                    }
                    if (rating !== null) break;
                }

                return { count, rating };
            }
        """)
        return info.get("count", 0), info.get("rating")
    except Exception:
        return 0, None


async def _extract_detail_images(page: Page) -> tuple[list[str], list[str]]:
    """상세 페이지 이미지 및 GIF 추출"""
    detail_imgs = []
    gif_urls = []

    try:
        # swiper 슬라이드 내 이미지 (썸네일 슬라이더)
        swiper_imgs = await page.evaluate("""
            () => {
                const imgs = document.querySelectorAll('.swiper-slide img, .swiper-wrapper img');
                return [...new Set([...imgs].map(img => img.src || img.dataset.src).filter(Boolean))];
            }
        """)
        for url in swiper_imgs:
            if url and "data:image" not in url and _is_product_image(url):
                if url.lower().endswith(".gif"):
                    gif_urls.append(url)
                else:
                    detail_imgs.append(url)

        # 상세 설명 영역 이미지 (React 렌더링 후)
        detail_area_imgs = await page.evaluate("""
            () => {
                const selectors = [
                    '[class*="detail"] img',
                    '[class*="Detail"] img',
                    '[class*="goods-detail"] img',
                    '[class*="GoodsDetail"] img',
                    'section img',
                ];
                const seen = new Set();
                const result = [];
                for (const sel of selectors) {
                    document.querySelectorAll(sel).forEach(img => {
                        const src = img.src || img.dataset.src;
                        if (src && !seen.has(src) && !src.includes('data:image')) {
                            seen.add(src);
                            result.push(src);
                        }
                    });
                }
                return result;
            }
        """)
        for url in detail_area_imgs:
            if not _is_product_image(url):
                continue
            if url.lower().endswith(".gif"):
                if url not in gif_urls:
                    gif_urls.append(url)
            else:
                if url not in detail_imgs:
                    detail_imgs.append(url)

    except Exception as e:
        logger.warning(f"[이미지] 추출 실패: {e}")

    return detail_imgs, gif_urls


async def _extract_video_urls(page: Page) -> list[str]:
    """MP4 영상 또는 YouTube iframe 링크 추출"""
    try:
        return await page.evaluate("""
            () => {
                const result = [];
                document.querySelectorAll('video source, video[src]').forEach(el => {
                    if (el.src) result.push(el.src);
                });
                document.querySelectorAll('iframe[src*="youtube"]').forEach(el => {
                    if (el.src) result.push(el.src);
                });
                return result;
            }
        """)
    except Exception:
        return []


async def _extract_keywords(page: Page) -> list[str]:
    """리뷰 기반 해시태그/소구점 키워드 추출"""
    try:
        tags = await page.evaluate("""
            () => {
                const candidates = document.querySelectorAll(
                    '[class*="tag"] span, [class*="Tag"] span, [class*="keyword"], [class*="hash"]'
                );
                return [...new Set([...candidates].map(el => el.innerText.trim()).filter(t => t && t.length < 20))];
            }
        """)
        return [t.replace("#", "").strip() for t in tags if t.strip()]
    except Exception:
        return []


async def download_asset(url: str, save_dir: str, filename: str) -> Optional[str]:
    """이미지/GIF/영상 URL을 로컬에 다운로드"""
    try:
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.oliveyoung.co.kr/",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
        return filepath
    except Exception as e:
        logger.warning(f"[다운로드 실패] {url}: {e}")
        return None
