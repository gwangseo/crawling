"""
올리브영 상품 상세 페이지 파싱 진단 스크립트 (React/Next.js 버전 대응)
메타 태그 방식이 올바르게 작동하는지 검증합니다.
"""
import asyncio
from playwright.async_api import async_playwright

TEST_URL = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000222833"


async def diagnose():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
        )
        page = await context.new_page()

        print(f"\n[1] 페이지 접속 중: {TEST_URL}")
        await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        print(f"[2] 현재 URL: {page.url}")
        print(f"[3] 페이지 제목: {await page.title()}")

        # ── 메타 태그 추출 ──
        print("\n[4] <meta property='eg:*'> 태그 값:")
        meta_fields = [
            "eg:itemName", "eg:brandName", "eg:originalPrice", "eg:salePrice",
            "eg:itemImage", "eg:itemId", "eg:brandId",
        ]
        meta_data = await page.evaluate("""
            (fields) => {
                const result = {};
                fields.forEach(prop => {
                    const el = document.querySelector(`meta[property="${prop}"]`);
                    result[prop] = el ? el.getAttribute('content') : '없음';
                });
                return result;
            }
        """, meta_fields)
        for k, v in meta_data.items():
            print(f"  {k}: {v}")

        # ── 찜/리뷰 수 ──
        print("\n[5] 찜·리뷰 수 추출 시도:")
        like_info = await page.evaluate("""
            () => {
                const results = [];
                const likeCandidates = [
                    ...document.querySelectorAll('[class*="like"]'),
                    ...document.querySelectorAll('[class*="wish"]'),
                ];
                likeCandidates.forEach(el => {
                    const text = el.innerText.trim();
                    if (text.match(/[\\d,]+/)) {
                        results.push({type: 'like', class: el.className.slice(0,60), text});
                    }
                });
                const reviewCandidates = document.querySelectorAll('[class*="review"], [class*="Review"]');
                reviewCandidates.forEach(el => {
                    const text = el.innerText.trim();
                    if (text.match(/^[\\d,.]+$/)) {
                        results.push({type: 'review', class: el.className.slice(0,60), text});
                    }
                });
                return results;
            }
        """)
        for item in like_info:
            print(f"  [{item['type']}] '{item['text']}' ← class: {item['class']}")

        # ── 이미지 URL ──
        print("\n[6] 이미지 URL 탐색:")
        img_urls = await page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                const selectors = [
                    '.swiper-slide img', '.swiper-wrapper img',
                    '[class*="detail"] img', '[class*="Detail"] img',
                    'section img',
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(img => {
                        const src = img.src || img.dataset?.src;
                        if (src && !seen.has(src) && !src.includes('data:image')) {
                            seen.add(src);
                            results.push({sel, src: src.slice(0, 100)});
                        }
                    });
                });
                return results.slice(0, 10);
            }
        """)
        for item in img_urls:
            print(f"  [{item['sel']}] {item['src']}")

        # ── GIF/영상 ──
        print("\n[7] GIF/영상 URL:")
        media_urls = await page.evaluate("""
            () => {
                const result = [];
                document.querySelectorAll('img[src$=".gif"], img[src*=".gif"]').forEach(el => {
                    result.push('gif: ' + el.src.slice(0, 100));
                });
                document.querySelectorAll('video source, video[src]').forEach(el => {
                    result.push('video: ' + (el.src || '').slice(0, 100));
                });
                return result;
            }
        """)
        for url in media_urls:
            print(f"  {url}")
        if not media_urls:
            print("  (없음)")

        # HTML 저장
        html = await page.content()
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("\n[8] 전체 HTML → debug_page.html 저장 완료")

        input("\n[Enter 키를 누르면 브라우저가 닫힙니다]")
        await browser.close()


asyncio.run(diagnose())
