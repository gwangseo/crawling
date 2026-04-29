"""
안티봇 우회 유틸리티
- Random Sleep, User-Agent 로테이션, Playwright Stealth 설정
"""
import random
import time
import asyncio
from loguru import logger

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def sleep_random(min_sec: float = 3.5, max_sec: float = 8.2) -> None:
    """동기 랜덤 슬립"""
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"[AntiBot] {delay:.1f}초 대기 중...")
    time.sleep(delay)


async def async_sleep_random(min_sec: float = 3.5, max_sec: float = 8.2) -> None:
    """비동기 랜덤 슬립"""
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"[AntiBot] {delay:.1f}초 대기 중...")
    await asyncio.sleep(delay)


def get_browser_launch_args() -> dict:
    """Playwright 브라우저 실행 인자 - 봇 탐지 우회용"""
    return {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ],
    }


def get_context_options() -> dict:
    """Playwright 컨텍스트 옵션 - 실제 사용자처럼 보이도록 설정"""
    return {
        "user_agent": get_random_user_agent(),
        "viewport": {"width": 1920, "height": 1080},
        "locale": "ko-KR",
        "timezone_id": "Asia/Seoul",
        "extra_http_headers": {
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        },
    }


async def apply_stealth_scripts(page) -> None:
    """navigator.webdriver 탐지 우회 스크립트 주입"""
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['ko-KR', 'ko', 'en-US', 'en'],
        });
        window.chrome = { runtime: {} };
    """)
