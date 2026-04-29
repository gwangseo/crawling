"""
대시보드 전용 DB 연결 + 쿼리 모듈
- psycopg2-binary 사용 (Streamlit Community Cloud 호환)
- database/models.py, crud.py 임포트 없음 → pgvector/psycopg(v3) 의존성 없음
- 순수 raw SQL로 필요한 데이터만 조회
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_engine = None
_Session = None

# SQLAlchemy가 PostgreSQL enum을 저장할 때 Python enum의 NAME(영문)을 사용함
# UI에서 사용하는 한국어 값 → DB 저장 영문 이름 매핑
CATEGORY_KO_TO_DB = {
    "스킨케어": "skincare",
    "마스크팩": "mask_pack",
    "클렌징": "cleansing",
    "선케어": "sun_care",
    "메이크업": "makeup",
    "네일": "nail",
    "맨즈": "mens",
    "헤어케어": "hair_care",
    "바디케어": "body_care",
    "기타": "etc",
}

# 반대 방향: DB 영문 이름 → UI 한국어 표시
CATEGORY_DB_TO_KO = {v: k for k, v in CATEGORY_KO_TO_DB.items()}


def _build_engine():
    url = os.getenv("DB_URL", "")
    if not url:
        raise RuntimeError(
            "DB_URL 환경변수가 설정되지 않았습니다. "
            "Streamlit Cloud Secrets에 DB_URL을 추가하세요."
        )
    url = url.replace("postgresql+psycopg://", "postgresql+psycopg2://")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)

    return create_engine(
        url,
        connect_args={"sslmode": "require"},
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
        pool_recycle=300,
    )


def _get_session():
    global _engine, _Session
    if _engine is None:
        _engine = _build_engine()
        _Session = sessionmaker(bind=_engine)
    return _Session()


def _to_korean_category(db_value: str) -> str:
    """DB 영문 enum값 → 한국어 표시명"""
    return CATEGORY_DB_TO_KO.get(db_value, db_value)


# ─────────────────────────────────────────────
# 상품 조회
# ─────────────────────────────────────────────

def search_products(category=None, keyword=None, limit=50):
    """상품 목록 반환 (카테고리/키워드 필터)"""
    db = _get_session()
    try:
        conditions = ["1=1"]
        params = {"limit": limit}
        if category:
            # UI 한국어 → DB 영문 변환 후 비교
            db_category = CATEGORY_KO_TO_DB.get(category, category)
            conditions.append("p.category::text = :category")
            params["category"] = db_category
        if keyword:
            conditions.append("(p.name ILIKE :kw OR p.brand ILIKE :kw)")
            params["kw"] = f"%{keyword}%"

        sql = text(f"""
            SELECT id::text, brand, name, category::text AS category,
                   original_price, discount_price, product_url, created_at
            FROM products p
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        rows = db.execute(sql, params).mappings().all()
        result = [dict(r) for r in rows]
        # category 값을 한국어로 변환해서 반환
        for r in result:
            r["category"] = _to_korean_category(r.get("category", ""))
        return result
    finally:
        db.close()


def get_product_detail(product_id: str):
    """단일 상품 레이아웃 + 태그 반환"""
    db = _get_session()
    try:
        # :pid::uuid 대신 CAST(:pid AS uuid) 사용 (SQLAlchemy text() 파싱 충돌 방지)
        layout_sql = text("""
            SELECT section_order, section_category::text AS section_category,
                   extracted_text, ai_description
            FROM product_layouts
            WHERE product_id = CAST(:pid AS uuid)
            ORDER BY section_order
        """)
        layouts = [
            dict(r) for r in db.execute(layout_sql, {"pid": product_id}).mappings().all()
        ]

        tag_sql = text("""
            SELECT keyword FROM tags WHERE product_id = CAST(:pid AS uuid)
        """)
        tags = [r["keyword"] for r in db.execute(tag_sql, {"pid": product_id}).mappings().all()]

        return {"layouts": layouts, "tags": tags}
    finally:
        db.close()


# ─────────────────────────────────────────────
# 에셋 조회
# ─────────────────────────────────────────────

def get_product_assets(product_id: str, asset_type=None):
    """상품 에셋 목록 반환"""
    db = _get_session()
    try:
        params = {"pid": product_id}
        type_filter = ""
        if asset_type:
            type_filter = "AND asset_type::text = :asset_type"
            params["asset_type"] = asset_type

        sql = text(f"""
            SELECT id::text, asset_type::text AS asset_type,
                   drive_url, original_filename
            FROM assets
            WHERE product_id = CAST(:pid AS uuid)
              AND drive_url IS NOT NULL
              {type_filter}
            ORDER BY created_at
        """)
        rows = db.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]
    finally:
        db.close()


# ─────────────────────────────────────────────
# 트렌드 조회
# ─────────────────────────────────────────────

def get_top_liked_products(limit=10):
    """찜 수 급상승 Top N (전주 대비)"""
    db = _get_session()
    try:
        sql = text("""
            WITH ranked AS (
                SELECT product_id, likes_count, review_count, rating, captured_at,
                       ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY captured_at DESC) AS rn
                FROM product_metrics
            ),
            latest AS (SELECT * FROM ranked WHERE rn = 1),
            prev   AS (SELECT * FROM ranked WHERE rn = 2)
            SELECT
                p.id::text,
                p.brand,
                p.name,
                p.category::text AS category,
                l.likes_count   AS current_likes,
                COALESCE(pv.likes_count, 0) AS prev_likes,
                (l.likes_count - COALESCE(pv.likes_count, 0)) AS likes_delta,
                l.review_count  AS current_reviews,
                l.rating,
                l.captured_at
            FROM latest l
            LEFT JOIN prev pv ON l.product_id = pv.product_id
            JOIN products p ON l.product_id = p.id
            ORDER BY likes_delta DESC
            LIMIT :limit
        """)
        rows = db.execute(sql, {"limit": limit}).mappings().all()
        result = [dict(r) for r in rows]
        for r in result:
            r["category"] = _to_korean_category(r.get("category", ""))
        return result
    finally:
        db.close()


def get_category_summary():
    """카테고리별 상품 수 / 평균 찜·리뷰·평점 요약"""
    db = _get_session()
    try:
        sql = text("""
            SELECT
                p.category::text AS category,
                COUNT(DISTINCT p.id) AS product_count,
                COALESCE(AVG(pm.likes_count), 0)::int   AS avg_likes,
                COALESCE(AVG(pm.review_count), 0)::int  AS avg_reviews,
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
        result = [dict(r) for r in rows]
        for r in result:
            r["category"] = _to_korean_category(r.get("category", ""))
        return result
    finally:
        db.close()
