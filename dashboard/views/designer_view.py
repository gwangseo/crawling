"""
Mode 2: 디자이너 뷰
- Pinterest 스타일 Masonry 갤러리
- 에셋 타입 필터 (썸네일 / 상세 이미지 / GIF)
"""
import streamlit as st

from dashboard.components.masonry_gallery import render_masonry_gallery

CATEGORY_OPTIONS = [
    "전체", "스킨케어", "마스크팩", "클렌징", "선케어",
    "메이크업", "네일", "맨즈", "헤어케어", "바디케어", "기타"
]

ASSET_TYPE_OPTIONS = {
    "전체": None,
    "썸네일": "thumbnail",
    "상세 이미지": "detail_image",
    "GIF": "gif",
    "영상": "video",
}


def _get_db():
    from database.session import SessionLocal
    return SessionLocal()


def render():
    st.header("디자이너 뷰 — 시각적 레퍼런스 탐색")

    # --- 필터 컨트롤 ---
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        category = st.selectbox("카테고리", CATEGORY_OPTIONS, key="designer_category")
    with col2:
        asset_type_label = st.selectbox("에셋 타입", list(ASSET_TYPE_OPTIONS.keys()), key="designer_asset_type")
        asset_type = ASSET_TYPE_OPTIONS[asset_type_label]
    with col3:
        keyword = st.text_input("브랜드 또는 상품명 검색", key="designer_keyword")

    st.divider()

    # --- AI 유사 이미지 검색 (서버 배포 시 활성화) ---
    with st.expander("이미지로 유사 무드 검색 (AI 기능)", expanded=False):
        st.info(
            "이 기능은 CLIP 임베딩 백엔드 서버가 필요합니다. "
            "Docker로 백엔드를 실행한 뒤 로컬에서 사용하세요 (`docker-compose up`)."
        )

    # --- 상품 목록 불러오기 ---
    try:
        from database import crud
        db = _get_db()
        cat = category if category != "전체" else None
        kw = keyword if keyword else None
        products_objs = crud.search_products(db, category=cat, keyword=kw, limit=50)
        products = [
            {"id": str(p.id), "brand": p.brand, "name": p.name}
            for p in products_objs
        ]
        db.close()
    except Exception as e:
        st.error(f"데이터베이스 연결 실패: {e}")
        return

    if not products:
        st.info("검색 결과가 없습니다.")
        return

    # --- 각 상품의 에셋 수집 및 갤러리 렌더링 ---
    all_assets = []
    try:
        db = _get_db()
        for product in products[:20]:
            asset_objs = crud.get_product_assets(db, product["id"], asset_type=asset_type)
            for a in asset_objs[:5]:
                if not a.drive_url:
                    continue
                all_assets.append({
                    "id": str(a.id),
                    "drive_url": a.drive_url,
                    "asset_type": a.asset_type.value if a.asset_type else None,
                    "brand": product["brand"],
                    "product_name": product["name"],
                })
        db.close()
    except Exception as e:
        st.error(f"에셋 로드 실패: {e}")
        return

    st.caption(f"총 {len(all_assets)}개 에셋 표시 중")

    if all_assets:
        render_masonry_gallery(all_assets, cols=4, show_caption=True)
    else:
        st.info("에셋이 없습니다. 크롤링 후 다시 확인하세요.")
