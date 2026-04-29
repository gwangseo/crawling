"""
올리브영 카테고리별 상품 URL 수집기
각 카테고리 목록 페이지를 순회하며 상품 상세 URL을 추출한다.
"""
import asyncio
import os
import re
from typing import Optional
from loguru import logger
from playwright.async_api import async_playwright, Page

from crawler.anti_bot import (
    get_browser_launch_args,
    get_context_options,
    apply_stealth_scripts,
    async_sleep_random,
)

# 올리브영 카테고리 코드 매핑
# dispCatNo는 실제 올리브영 카테고리 분류 번호 (2026년 4월 기준)
_BASE = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"
_PARAMS = "&fltDispCatNo=&prdSort=01&pageIdx={page}&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds="

CATEGORY_MAP = {
    "스킨케어": {
        "enum": "skincare",
        "url": f"{_BASE}?dispCatNo=10000010001{_PARAMS}",
    },
    "메이크업": {
        "enum": "makeup",
        "url": f"{_BASE}?dispCatNo=10000010002{_PARAMS}",
    },
    "선케어": {
        "enum": "sun_care",
        "url": f"{_BASE}?dispCatNo=10000010011{_PARAMS}",
    },
    "바디케어": {
        "enum": "body_care",
        "url": f"{_BASE}?dispCatNo=100000100030025{_PARAMS}",
    },
    "마스크팩": {
        "enum": "mask_pack",
        "url": f"{_BASE}?dispCatNo=100000100010014{_PARAMS}",
    },
    "클렌징": {
        "enum": "cleansing",
        "url": f"{_BASE}?dispCatNo=100000100010015{_PARAMS}",
    },
    "맨즈": {
        "enum": "mens",
        "url": f"{_BASE}?dispCatNo=100000100010017{_PARAMS}",
    },
    "기타": {
        "enum": "etc",
        "url": f"{_BASE}?dispCatNo=100000100010018{_PARAMS}",
    },
}

MAX_PRODUCTS_PER_CATEGORY = int(os.getenv("CRAWL_PRODUCTS_PER_CATEGORY", "30"))


async def collect_product_urls_from_page(page: Page, list_url: str) -> list[str]:
    """카테고리 목록 페이지 1장에서 상품 상세 URL 추출"""
    try:
        await page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
        # React 렌더링 대기 - 상품 링크가 DOM에 나타날 때까지 최대 10초 대기
        try:
            await page.wait_for_selector("a[href*='getGoodsDetail']", timeout=10000)
        except Exception:
            # 링크가 없으면 추가로 3초 더 대기 후 재시도
            await asyncio.sleep(3)

        links = await page.eval_on_selector_all(
            "a[href*='getGoodsDetail']",
            "elements => elements.map(el => el.href)"
        )

        seen = set()
        valid = []
        for link in links:
            if "getGoodsDetail" in link and "goodsNo" in link:
                m = re.search(r"goodsNo=([A-Z0-9]+)", link)
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    valid.append(link)

        logger.debug(f"[목록] {len(valid)}개 URL 추출")
        return valid
    except Exception as e:
        logger.warning(f"[목록] 페이지 로드 실패: {e}")
        return []


async def collect_category_product_urls(
    page: Page,
    category_name: str,
    category_info: dict,
    max_count: int = MAX_PRODUCTS_PER_CATEGORY,
) -> list[dict]:
    """
    카테고리 목록 페이지를 순회하며 상품 URL 수집
    반환: [{"oliveyoung_id": str, "url": str, "category": str}]
    """
    collected = []
    page_idx = 1

    while len(collected) < max_count:
        list_url = category_info["url"].format(page=page_idx)
        logger.info(f"[{category_name}] 페이지 {page_idx} 수집 중... (현재 {len(collected)}개)")

        urls = await collect_product_urls_from_page(page, list_url)
        if not urls:
            logger.info(f"[{category_name}] 더 이상 상품 없음, 수집 종료")
            break

        for url in urls:
            if len(collected) >= max_count:
                break
            # URL에서 goodsNo 추출
            match = re.search(r"goodsNo=([A-Z0-9]+)", url)
            if match:
                goods_no = match.group(1)
                collected.append({
                    "oliveyoung_id": goods_no,
                    "url": url,
                    "category": category_info["enum"],
                    "category_name": category_name,
                })

        page_idx += 1
        await async_sleep_random(2.0, 5.0)

    logger.info(f"[{category_name}] 총 {len(collected)}개 URL 수집 완료")
    return collected


async def collect_all_categories() -> list[dict]:
    """
    전체 10개 카테고리에서 상품 URL 수집
    반환: 전체 상품 메타 리스트 (최대 300개)
    """
    all_products = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(**get_browser_launch_args())
        context = await browser.new_context(**get_context_options())
        page = await context.new_page()
        await apply_stealth_scripts(page)

        for category_name, category_info in CATEGORY_MAP.items():
            logger.info(f"=== 카테고리 수집 시작: {category_name} ===")
            try:
                products = await collect_category_product_urls(page, category_name, category_info)
                all_products.extend(products)
            except Exception as e:
                logger.error(f"[{category_name}] 카테고리 수집 오류: {e}")

            # 카테고리 간 대기
            await async_sleep_random(5.0, 10.0)

        await browser.close()

    logger.info(f"=== 전체 URL 수집 완료: 총 {len(all_products)}개 ===")
    return all_products
