"""
DB CRUD 로직 - 중복 분기 처리가 핵심
- 신규 상품: products INSERT + assets 다운로드 트리거
- 기존 상품: product_metrics만 UPDATE (에셋 재다운로드 없음)
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from loguru import logger

from database.models import (
    Product, ProductMetric, Asset, ProductLayout, Tag,
    CategoryEnum, AssetTypeEnum, SectionCategoryEnum
)


def get_product_by_oliveyoung_id(db: Session, oliveyoung_id: str) -> Optional[Product]:
    return db.query(Product).filter(Product.oliveyoung_id == oliveyoung_id).first()


def create_product(db: Session, product_data: dict) -> Product:
    product = Product(
        oliveyoung_id=product_data["oliveyoung_id"],
        brand=product_data["brand"],
        name=product_data["name"],
        category=product_data["category"],
        original_price=product_data.get("original_price"),
        discount_price=product_data.get("discount_price"),
        product_url=product_data["product_url"],
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    logger.info(f"[DB] 신규 상품 저장: {product.brand} - {product.name}")
    return product


def upsert_product_metric(db: Session, product_id: UUID, likes: int, reviews: int, rating: float) -> ProductMetric:
    """매주 수집 시 지표 시계열 INSERT (트렌드 추적용)"""
    metric = ProductMetric(
        product_id=product_id,
        likes_count=likes,
        review_count=reviews,
        rating=rating,
        captured_at=datetime.utcnow(),
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def create_asset(db: Session, product_id: UUID, asset_data: dict) -> Asset:
    asset = Asset(
        product_id=product_id,
        asset_type=asset_data["asset_type"],
        drive_file_id=asset_data.get("drive_file_id"),
        drive_url=asset_data.get("drive_url"),
        original_filename=asset_data.get("original_filename"),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def create_tags(db: Session, product_id: UUID, keywords: list[str]) -> None:
    for keyword in keywords:
        existing = db.query(Tag).filter(
            Tag.product_id == product_id,
            Tag.keyword == keyword
        ).first()
        if not existing:
            tag = Tag(product_id=product_id, keyword=keyword)
            db.add(tag)
    db.commit()


def create_layout_sections(db: Session, product_id: UUID, sections: list[dict]) -> None:
    for section in sections:
        layout = ProductLayout(
            product_id=product_id,
            section_order=section["order"],
            section_category=section["category"],
            extracted_text=section.get("text"),
            ai_description=section.get("description"),
        )
        db.add(layout)
    db.commit()


def update_asset_embedding(db: Session, asset_id: UUID, embedding: list[float]) -> None:
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset:
        asset.visual_embedding = embedding
        db.commit()


def search_products(
    db: Session,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if keyword:
        query = query.filter(
            Product.name.ilike(f"%{keyword}%") |
            Product.brand.ilike(f"%{keyword}%")
        )
    return query.order_by(Product.created_at.desc()).offset(offset).limit(limit).all()


def get_product_assets(db: Session, product_id, asset_type: Optional[str] = None) -> list[Asset]:
    """상품의 에셋 목록 조회 (asset_type 필터 선택적)"""
    import uuid as uuid_lib
    query = db.query(Asset).filter(Asset.product_id == uuid_lib.UUID(str(product_id)))
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    return query.order_by(Asset.created_at).all()


def get_top_liked_products(db: Session, limit: int = 10) -> list[dict]:
    """
    최근 2회 수집 데이터를 비교하여 찜 수 급상승 상품 Top N 반환
    """
    from sqlalchemy import text

    sql = text("""
        WITH ranked AS (
            SELECT
                pm.product_id,
                pm.likes_count,
                pm.review_count,
                pm.rating,
                pm.captured_at,
                ROW_NUMBER() OVER (PARTITION BY pm.product_id ORDER BY pm.captured_at DESC) AS rn
            FROM product_metrics pm
        ),
        latest AS (SELECT * FROM ranked WHERE rn = 1),
        prev   AS (SELECT * FROM ranked WHERE rn = 2)
        SELECT
            p.id,
            p.brand,
            p.name,
            p.category,
            l.likes_count AS current_likes,
            COALESCE(pv.likes_count, 0) AS prev_likes,
            (l.likes_count - COALESCE(pv.likes_count, 0)) AS likes_delta,
            l.review_count AS current_reviews,
            l.rating,
            l.captured_at
        FROM latest l
        LEFT JOIN prev pv ON l.product_id = pv.product_id
        JOIN products p ON l.product_id = p.id
        ORDER BY likes_delta DESC
        LIMIT :limit
    """)
    result = db.execute(sql, {"limit": limit}).mappings().all()
    return [dict(r) for r in result]
