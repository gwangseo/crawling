from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database.session import get_db
from database import crud
from database.models import CategoryEnum

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.get("")
def search_products(
    category: Optional[str] = Query(None, description="카테고리 (예: 스킨케어, 마스크팩)"),
    keyword: Optional[str] = Query(None, description="브랜드명 또는 상품명 검색"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    products = crud.search_products(db, category=category, keyword=keyword, limit=limit, offset=offset)
    return [
        {
            "id": str(p.id),
            "oliveyoung_id": p.oliveyoung_id,
            "brand": p.brand,
            "name": p.name,
            "category": p.category.value if p.category else None,
            "original_price": p.original_price,
            "discount_price": p.discount_price,
            "product_url": p.product_url,
            "created_at": p.created_at.isoformat(),
        }
        for p in products
    ]


@router.get("/{product_id}/detail")
def get_product_detail(product_id: str, db: Session = Depends(get_db)):
    from database.models import Product
    import uuid as uuid_lib
    product = db.query(Product).filter(Product.id == uuid_lib.UUID(product_id)).first()
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    return {
        "id": str(product.id),
        "brand": product.brand,
        "name": product.name,
        "category": product.category.value if product.category else None,
        "original_price": product.original_price,
        "discount_price": product.discount_price,
        "product_url": product.product_url,
        "tags": [t.keyword for t in product.tags],
        "layouts": [
            {
                "order": l.section_order,
                "section": l.section_category.value if l.section_category else None,
                "text": l.extracted_text,
                "description": l.ai_description,
            }
            for l in sorted(product.layouts, key=lambda x: x.section_order)
        ],
    }
