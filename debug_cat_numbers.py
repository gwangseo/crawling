"""올리브영 카테고리 번호 자동 탐색"""
import asyncio
from playwright.async_api import async_playwright

async def find_categories():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="ko-KR",
        )
        page = await context.new_page()

        # 10019 ~ 10035 범위 탐색
        for cat_no_suffix in range(19, 36):
            disp_cat_no = f"10000010001{cat_no_suffix:04d}"
            url = f"https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo={disp_cat_no}&fltDispCatNo=&prdSort=01&pageIdx=1&rowsPerPage=24&searchTypeSort=btn_A&plusButtonFlag=N&isLoginYn=N&alertYn=&P_LANG=ko&attrIds="
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                title = await page.title()
                final_url = page.url
                links = await page.eval_on_selector_all(
                    "a[href*='getGoodsDetail']",
                    "els => els.length"
                )
                if links > 0 and "스킨케어" not in title:
                    print(f"[발견] dispCatNo={disp_cat_no} → 제목: {title[:40]} | 상품 {links}개")
                elif links > 0:
                    pass  # 스킨케어 리다이렉트는 출력 안 함
                else:
                    print(f"[없음] dispCatNo={disp_cat_no} → {title[:30]}")
            except Exception as e:
                print(f"[오류] dispCatNo={disp_cat_no}: {e}")

        await browser.close()

asyncio.run(find_categories())
