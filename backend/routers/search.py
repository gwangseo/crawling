from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid as uuid_lib

from database.session import get_db

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


@router.post("/visual-similar")
async def search_visual_similar(
    file: UploadFile = File(..., description="레퍼런스 이미지 업로드"),
    limit: int = Query(12, ge=1, le=50),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    업로드한 이미지와 시각적으로 유사한 에셋을 pgvector 코사인 유사도로 검색
    (Phase 3 AI 파이프라인 구현 후 활성화)
    """
    try:
        from ai.embedder import get_image_embedding_from_bytes
        from sqlalchemy import text

        image_bytes = await file.read()
        query_vector = get_image_embedding_from_bytes(image_bytes)

        # pgvector 코사인 유사도 검색
        category_filter = "AND p.category = :category" if category else ""
        sql = text(f"""
            SELECT
                a.id AS asset_id,
                a.drive_url,
                a.asset_type,
                p.brand,
                p.name,
                p.category,
                1 - (a.visual_embedding <=> :query_vector::vector) AS similarity
            FROM assets a
            JOIN products p ON a.product_id = p.id
            WHERE a.visual_embedding IS NOT NULL
            {category_filter}
            ORDER BY a.visual_embedding <=> :query_vector::vector
            LIMIT :limit
        """)

        params = {"query_vector": str(query_vector), "limit": limit}
        if category:
            params["category"] = category

        rows = db.execute(sql, params).mappings().all()
        return [
            {
                "asset_id": str(r["asset_id"]),
                "drive_url": r["drive_url"],
                "asset_type": r["asset_type"],
                "brand": r["brand"],
                "product_name": r["name"],
                "category": r["category"],
                "similarity": round(float(r["similarity"]), 4),
            }
            for r in rows
        ]

    except ImportError:
        return {"message": "AI 임베딩 모듈이 아직 설정되지 않았습니다. Phase 3 설정 후 사용 가능합니다."}
    except Exception as e:
        return {"error": str(e)}


@router.get("/keywords")
def search_by_keyword(
    keyword: str = Query(..., description="검색할 키워드/해시태그"),
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """리뷰 기반 키워드로 상품 검색"""
    from sqlalchemy import text

    category_filter = "AND p.category = :category" if category else ""
    sql = text(f"""
        SELECT DISTINCT
            p.id, p.brand, p.name, p.category, p.product_url,
            t.keyword
        FROM tags t
        JOIN products p ON t.product_id = p.id
        WHERE t.keyword ILIKE :keyword
        {category_filter}
        LIMIT :limit
    """)

    params = {"keyword": f"%{keyword}%", "limit": limit}
    if category:
        params["category"] = category

    rows = db.execute(sql, params).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "brand": r["brand"],
            "name": r["name"],
            "category": r["category"],
            "product_url": r["product_url"],
            "matched_keyword": r["keyword"],
        }
        for r in rows
    ]
