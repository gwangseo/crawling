"""
APScheduler 크론잡 - 매주 금요일 18:00 크롤링 파이프라인 자동 실행
"""
import asyncio
import os
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()


def run_pipeline():
    """크롤링 파이프라인 동기 래퍼 (APScheduler 호환)"""
    from crawler.pipeline import run_crawling_pipeline
    from backend.monitoring import send_slack_report

    logger.info("[스케줄러] 크롤링 파이프라인 트리거")
    try:
        stats = asyncio.run(run_crawling_pipeline())
        send_slack_report(
            title="올리브영 주간 크롤링 완료",
            stats=stats,
            is_error=False,
        )
        logger.info("[스케줄러] 완료 리포트 Slack 전송 완료")
    except Exception as e:
        logger.error(f"[스케줄러] 파이프라인 오류: {e}")
        send_slack_report(
            title="크롤링 파이프라인 오류 발생",
            stats={"error_message": str(e)},
            is_error=True,
        )


def start_scheduler():
    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    # 매주 금요일 18:00 실행 (15시간 내에 토요일 09:00까지 완료 목표)
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(
            day_of_week="fri",
            hour=18,
            minute=0,
            timezone="Asia/Seoul",
        ),
        id="oliveyoung_weekly_crawl",
        name="올리브영 주간 크롤링",
        misfire_grace_time=3600,  # 1시간 내 지연 허용
        replace_existing=True,
    )

    logger.info("[스케줄러] 시작 - 매주 금요일 18:00 KST 크롤링 예정")
    logger.info(f"[스케줄러] 다음 실행 예정: {scheduler.get_jobs()[0].next_run_time}")
    scheduler.start()


if __name__ == "__main__":
    # 개발 환경에서 즉시 실행 테스트용
    import sys
    if "--run-now" in sys.argv:
        logger.info("[수동 실행] 파이프라인 즉시 실행")
        run_pipeline()
    else:
        start_scheduler()
