"""
FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.routers import products, assets, trends, search

app = FastAPI(
    title="K-Beauty Reference DB API",
    description="닥터코리아 올리브영 레퍼런스 수집 및 분석 시스템",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(assets.router)
app.include_router(trends.router)
app.include_router(search.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "K-Beauty Reference DB"}


@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI 서버 시작")
