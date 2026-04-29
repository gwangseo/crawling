import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey,
    Enum, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from database.session import Base


class CategoryEnum(str, PyEnum):
    skincare = "스킨케어"
    mask_pack = "마스크팩"
    cleansing = "클렌징"
    sun_care = "선케어"
    makeup = "메이크업"
    nail = "네일"
    mens = "맨즈"
    hair_care = "헤어케어"
    body_care = "바디케어"
    etc = "기타"


class AssetTypeEnum(str, PyEnum):
    thumbnail = "thumbnail"
    detail_image = "detail_image"
    gif = "gif"
    video = "video"


class SectionCategoryEnum(str, PyEnum):
    hook = "Hook"
    problem = "Problem"
    solution = "Solution"
    proof = "Proof"
    how_to = "How-to"
    ingredient = "Ingredient"
    other = "Other"


class Product(Base):
    """상품 마스터 테이블 - 올리브영 상품 기본 정보"""
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oliveyoung_id = Column(String(50), unique=True, nullable=False, index=True)
    brand = Column(String(100), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    category = Column(Enum(CategoryEnum), nullable=False, index=True)
    original_price = Column(Integer, nullable=True)
    discount_price = Column(Integer, nullable=True)
    product_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    metrics = relationship("ProductMetric", back_populates="product", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="product", cascade="all, delete-orphan")
    layouts = relationship("ProductLayout", back_populates="product", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="product", cascade="all, delete-orphan")


class ProductMetric(Base):
    """주간 트렌드 추적용 시계열 테이블 - COO 대시보드의 핵심 데이터"""
    __tablename__ = "product_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    likes_count = Column(Integer, default=0)
    review_count = Column(Integer, default=0)
    rating = Column(Float, nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    product = relationship("Product", back_populates="metrics")


class Asset(Base):
    """시각 에셋 테이블 - Google Drive 링크 및 이미지 임베딩 벡터"""
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type = Column(Enum(AssetTypeEnum), nullable=False)
    drive_file_id = Column(String(200), nullable=True)
    drive_url = Column(Text, nullable=True)
    original_filename = Column(String(300), nullable=True)
    # pgvector: 512차원 벡터 (CLIP ViT-B/32 기준)
    visual_embedding = Column(Vector(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="assets")


class ProductLayout(Base):
    """PM 상세페이지 구조화 테이블 - GPT-4o Vision이 태깅한 섹션 구조"""
    __tablename__ = "product_layouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    section_order = Column(Integer, nullable=False)
    section_category = Column(Enum(SectionCategoryEnum), nullable=False)
    extracted_text = Column(Text, nullable=True)
    ai_description = Column(Text, nullable=True)

    product = relationship("Product", back_populates="layouts")


class Tag(Base):
    """키워드/해시태그 테이블 - 리뷰 기반 소구점 키워드"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    keyword = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("product_id", "keyword", name="uq_product_keyword"),
    )

    product = relationship("Product", back_populates="tags")
