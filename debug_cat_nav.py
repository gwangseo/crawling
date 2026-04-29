"""올리브영 메인 네비게이션에서 실제 카테고리 URL 추출"""
import asyncio
from playwright.async_api import async_playwright

TARGET_CATEGORIES = ["메이크업", "네일", "헤어케어", "헤어", "바디케어", "바디"]

async def find_nav_categories():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="ko-KR",
        )
        page = await context.new_page()

        print("올리브영 메인 페이지 접속 중...")
        await page.goto("https://www.oliveyoung.co.kr/store/main/main.do", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)

        # 카테고리 목록 링크 전체 추출
        all_links = await page.evaluate("""
            () => {
                const result = [];
                document.querySelectorAll('a[href*="getMCategoryList"], a[href*="dispCatNo"]').forEach(el => {
                    const href = el.href;
                    const text = el.innerText.trim();
                    if (href && text) result.push({text, href});
                });
                return result;
            }
        """)

        print(f"\n전체 카테고리 링크 수: {len(all_links)}")
        print("\n=== 카테고리 목록 ===")
        seen = set()
        for item in all_links:
            key = item['text'][:20]
            if key not in seen and item['href']:
                seen.add(key)
                import re
                m = re.search(r'dispCatNo=(\d+)', item['href'])
                if m:
                    print(f"  '{item['text'][:30]}' → dispCatNo={m.group(1)}")

        await browser.close()

asyncio.run(find_nav_categories())
