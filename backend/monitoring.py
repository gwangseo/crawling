"""
Slack Webhook 모니터링 모듈
- 크롤링 완료 리포트 전송
- Critical 에러 즉시 알림
"""
import os
from datetime import datetime
from loguru import logger
from slack_sdk.webhook import WebhookClient


SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def send_slack_report(title: str, stats: dict, is_error: bool = False) -> None:
    if not SLACK_WEBHOOK_URL:
        logger.warning("[Slack] SLACK_WEBHOOK_URL이 설정되지 않아 알림을 건너뜁니다.")
        return

    try:
        client = WebhookClient(SLACK_WEBHOOK_URL)
        color = "#FF0000" if is_error else "#36A64F"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if is_error:
            text = f"*오류 메시지:* {stats.get('error_message', '알 수 없는 오류')}"
        else:
            text = (
                f"*신규 상품:* {stats.get('new', 0)}개\n"
                f"*지표 업데이트:* {stats.get('updated', 0)}개\n"
                f"*오류:* {stats.get('error', 0)}개\n"
                f"*실행 시각:* {now}"
            )

        response = client.send(
            attachments=[{
                "color": color,
                "title": f"[K-Beauty DB] {title}",
                "text": text,
                "footer": "닥터코리아 크롤링 시스템",
            }]
        )
        if response.status_code != 200:
            logger.warning(f"[Slack] 전송 실패: {response.status_code}")
    except Exception as e:
        logger.error(f"[Slack] 알림 오류: {e}")


def send_critical_alert(message: str) -> None:
    """Critical 에러 즉시 알림"""
    send_slack_report(title="CRITICAL 에러 발생", stats={"error_message": message}, is_error=True)
