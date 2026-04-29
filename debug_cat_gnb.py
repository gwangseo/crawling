"""올리브영 GNB 카테고리 코드 자동 추출 (파일 저장 버전)"""
import asyncio
import re
import json
from playwright.async_api import async_playwright

TARGET_KW = ["메이크업", "네일", "헤어", "바디", "스킨케어", "마스크", "클렌징", "선케어", "맨즈", "기타"]

async def find_categories():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ko-KR",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        found = {}

        for kw in TARGET_KW:
            print(f"\n[{kw}] 탐색 중...")
            # 직접 스킨케어 URL 패턴으로 시작 후 다른 카테고리 찾기
            # 각 카테고리를 올리브영 검색으로 접근
            try:
                search_url = f"https://www.oliveyoung.co.kr/store/search/getSearchMain.do?query={kw}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)

                # 카테고리 링크 추출
                links = await page.evaluate("""
                    () => {
                        const results = [];
                        document.querySelectorAll('a').forEach(el => {
                            const href = el.href || '';
                            if (href.includes('getMCategoryList') && href.includes('dispCatNo')) {
                                const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g,' ');
                                results.push({text: text.slice(0,30), href});
                            }
                        });
                        return results;
                    }
                """)

                for item in links:
                    m = re.search(r'dispCatNo=(\d+)', item['href'])
                    if m:
                        cat_no = m.group(1)
                        print(f"  발견: '{item['text'][:25]}' → {cat_no}")
                        found[item['text'][:25]] = cat_no

            except Exception as e:
                print(f"  오류: {e}")

        # GNB에서 한번에 추출
        print("\n[GNB 전체 카테고리 추출] 메인 페이지 접속...")
        await page.goto("https://www.oliveyoung.co.kr/store/main/main.do",
                        wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(4)

        # 마우스를 카테고리 메뉴에 올려 GNB 전체 로드
        try:
            # GNB의 카테고리 목록 버튼 hover
            for selector in ["[class*='gnb']", "[class*='GNB']", "[class*='category']", "nav"]:
                try:
                    await page.hover(selector, timeout=2000)
                    await asyncio.sleep(1)
                    break
                except Exception:
                    pass
        except Exception:
            pass

        all_links = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('a').forEach(el => {
                    const href = el.href || '';
                    if (href.includes('getMCategoryList') && href.includes('dispCatNo')) {
                        const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g,' ');
                        if (text.length > 0 && text.length < 30) {
                            results.push({text, href});
                        }
                    }
                });
                return results;
            }
        """)

        print(f"\n=== GNB 카테고리 링크 {len(all_links)}개 ===")
        seen = set()
        for item in all_links:
            m = re.search(r'dispCatNo=(\d+)', item['href'])
            if m:
                cat_no = m.group(1)
                key = f"{item['text'][:15]}_{cat_no}"
                if key not in seen:
                    seen.add(key)
                    print(f"  '{item['text'][:25]}' → {cat_no}")
                    found[item['text'][:25]] = cat_no

        # 결과 파일 저장
        with open("category_codes.json", "w", encoding="utf-8") as f:
            json.dump(found, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장 완료: category_codes.json")

        await browser.close()

asyncio.run(find_categories())
