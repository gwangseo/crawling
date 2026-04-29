"""0개가 나오는 카테고리 URL 진단"""
import asyncio
from playwright.async_api import async_playwright

TEST_CATS = {
    "메이크업": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010006&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds=",
    "네일":     "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010007&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds=",
    "헤어케어": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010008&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds=",
    "바디케어": "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100010009&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds=",
}

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="ko-KR",
        )
        page = await context.new_page()

        for name, url in TEST_CATS.items():
            print(f"\n[{name}] 테스트 중...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)
                title = await page.title()
                links = await page.eval_on_selector_all(
                    "a[href*='getGoodsDetail']",
                    "els => els.map(e => e.href)"
                )
                redirect_url = page.url
                print(f"  제목: {title[:50]}")
                print(f"  최종 URL: {redirect_url[:80]}")
                print(f"  상품 링크 수: {len(links)}")
                if links:
                    print(f"  첫 링크: {links[0][:80]}")
            except Exception as e:
                print(f"  오류: {e}")

        await browser.close()

asyncio.run(check())
