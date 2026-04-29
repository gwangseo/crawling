from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from database import crud

router = APIRouter(prefix="/api/v1/trends", tags=["Trends"])


@router.get("/top-liked")
def get_top_liked(
    limit: int = Query(10, ge=1, le=50, description="상위 N개 반환"),
    db: Session = Depends(get_db),
):
    """
    주간 찜 수 급상승 상품 Top N
    전주 대비 증감률(likes_delta) 기준 정렬
    """
    results = crud.get_top_liked_products(db, limit=limit)
    return [
        {
            **r,
            "id": str(r["id"]) if r.get("id") else None,
            "captured_at": r["captured_at"].isoformat() if r.get("captured_at") else None,
        }
        for r in results
    ]


@router.get("/category-summary")
def get_category_summary(db: Session = Depends(get_db)):
    """카테고리별 상품 수 및 평균 찜 수 요약"""
    from sqlalchemy import text
    sql = text("""
        SELECT
            p.category,
            COUNT(DISTINCT p.id) AS product_count,
            COALESCE(AVG(pm.likes_count), 0)::int AS avg_likes,
            COALESCE(AVG(pm.review_count), 0)::int AS avg_reviews,
            COALESCE(AVG(pm.rating), 0)::numeric(3,1) AS avg_rating
        FROM products p
        LEFT JOIN (
            SELECT DISTINCT ON (product_id) *
            FROM product_metrics
            ORDER BY product_id, captured_at DESC
        ) pm ON p.id = pm.product_id
        GROUP BY p.category
        ORDER BY avg_likes DESC
    """)
    rows = db.execute(sql).mappings().all()
    return [dict(r) for r in rows]
