from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv
import os

load_dotenv(encoding="utf-8")

DB_URL = os.getenv("DB_URL", "postgresql://kbeauty:kbeauty_pass@localhost:5432/kbeauty_db")

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=300,       # 5분마다 연결 재생성 (Supabase idle timeout 대비)
    pool_size=3,
    max_overflow=5,
    connect_args={"sslmode": "require"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
