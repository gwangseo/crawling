"""새 카테고리 URL 4개 동작 검증"""
import asyncio
from playwright.async_api import async_playwright

TEST = {
    "스킨케어(새)":  "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=10000010001&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds=",
    "메이크업(새)":  "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=10000010002&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds=",
    "선케어(새)":    "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=10000010011&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds=",
    "바디케어(새)":  "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100030025&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds=",
}

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="ko-KR",
        )
        page = await context.new_page()

        for name, url in TEST.items():
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                try:
                    await page.wait_for_selector("a[href*='getGoodsDetail']", timeout=8000)
                except Exception:
                    await asyncio.sleep(3)
                links = await page.eval_on_selector_all(
                    "a[href*='getGoodsDetail']",
                    "els => els.length"
                )
                title = await page.title()
                status = "OK" if links > 0 else "FAIL"
                print(f"[{status}] {name}: {links}개 상품 | 제목: {title[:35]}")
            except Exception as e:
                print(f"[ERR] {name}: {e}")

        await browser.close()

asyncio.run(verify())
