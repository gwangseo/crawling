"""
DB 초기화 스크립트 - 최초 1회 실행
pgvector 확장 활성화 후 모든 테이블 생성
"""
from sqlalchemy import text
from loguru import logger

from database.session import engine, Base
from database import models  # noqa: F401 - 모델 import로 Base에 등록


def init_database():
    logger.info("DB 초기화 시작...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        logger.info("pgvector 확장 활성화 완료")

    Base.metadata.create_all(bind=engine)
    logger.info("모든 테이블 생성 완료")
    logger.info("테이블 목록: products, product_metrics, assets, product_layouts, tags")


if __name__ == "__main__":
    init_database()
