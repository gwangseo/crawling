"""
product_detail.py 파서 단독 테스트 스크립트
실행: python test_parser.py
"""
import asyncio
from playwright.async_api import async_playwright
from crawler.product_detail import parse_product_detail
from crawler.anti_bot import get_browser_launch_args, get_context_options, apply_stealth_scripts

TEST_URL = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000222833"


async def main():
    print(f"\n테스트 URL: {TEST_URL}\n")
    async with async_playwright() as p:
        browser = await p.chromium.launch(**get_browser_launch_args())
        context = await browser.new_context(**get_context_options())
        page = await context.new_page()
        await apply_stealth_scripts(page)

        result = await parse_product_detail(page, TEST_URL)
        await browser.close()

    if result:
        print("=== 파싱 결과 ===")
        print(f"  브랜드     : {result.get('brand')}")
        print(f"  상품명     : {result.get('name')}")
        print(f"  정가       : {result.get('original_price')}")
        print(f"  할인가     : {result.get('discount_price')}")
        print(f"  찜 수      : {result.get('likes_count')}")
        print(f"  리뷰 수    : {result.get('review_count')}")
        print(f"  평점       : {result.get('rating')}")
        print(f"  썸네일     : {len(result.get('thumbnail_urls', []))}장")
        print(f"  상세이미지 : {len(result.get('detail_image_urls', []))}장")
        print(f"  GIF        : {len(result.get('gif_urls', []))}개")
        print(f"  영상       : {len(result.get('video_urls', []))}개")
        print(f"  키워드     : {result.get('keywords')}")
        print(f"\n  썸네일 URL (첫 번째): {result.get('thumbnail_urls', [None])[0]}")
    else:
        print("파싱 실패!")


if __name__ == "__main__":
    asyncio.run(main())
