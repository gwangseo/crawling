"""
Mode 1: 기획자(PM) 뷰
- 상세 페이지 구조 타임라인 (Hook → Problem → Solution 등)
- 카테고리별 소구점 키워드 빈도 차트
"""
import streamlit as st
import plotly.express as px
import pandas as pd

SECTION_COLORS = {
    "Hook": "#FF6B6B",
    "Problem": "#FFB347",
    "Solution": "#98D8C8",
    "Proof": "#87CEEB",
    "How-to": "#DDA0DD",
    "Ingredient": "#90EE90",
    "Other": "#D3D3D3",
}

CATEGORY_OPTIONS = [
    "전체", "스킨케어", "마스크팩", "클렌징", "선케어",
    "메이크업", "네일", "맨즈", "헤어케어", "바디케어", "기타"
]


def render():
    st.header("기획자(PM) 뷰 — 구조 분석 & 카피라이팅 인사이트")

    col1, col2 = st.columns([1, 3])
    with col1:
        selected_category = st.selectbox("카테고리", CATEGORY_OPTIONS, key="pm_category")
        keyword = st.text_input("상품명/브랜드 검색", key="pm_keyword")

    # --- 상품 목록 ---
    try:
        from dashboard.db import search_products
        cat = selected_category if selected_category != "전체" else None
        kw = keyword if keyword else None
        products = search_products(category=cat, keyword=kw, limit=30)
    except Exception as e:
        st.error(f"데이터베이스 연결 실패: {e}")
        return

    if not products:
        st.info("검색 결과가 없습니다.")
        return

    with col2:
        st.caption(f"{len(products)}개 상품 검색됨")

    product_options = {f"{p['brand']} - {p['name']}": p["id"] for p in products}
    selected_label = st.selectbox("분석할 상품 선택", list(product_options.keys()), key="pm_product_select")

    if not selected_label:
        return

    selected_id = product_options[selected_label]

    # --- 상품 상세 조회 ---
    try:
        from dashboard.db import get_product_detail
        detail = get_product_detail(selected_id)
    except Exception as e:
        st.error(f"상세 정보 로드 실패: {e}")
        return

    col_left, col_right = st.columns([1, 1])

    # --- 상세 페이지 구조 타임라인 ---
    with col_left:
        st.subheader("상세 페이지 구조 타임라인")
        layouts = detail.get("layouts", [])
        if layouts:
            for section in layouts:
                section_name = section.get("section_category", "Other")
                color = SECTION_COLORS.get(section_name, "#D3D3D3")
                with st.container():
                    st.markdown(
                        f"""<div style="
                            background:{color};
                            padding:10px 16px;
                            border-radius:8px;
                            margin-bottom:6px;
                            color:#333;
                            font-weight:bold;
                        ">{section['section_order']}. {section_name}</div>""",
                        unsafe_allow_html=True,
                    )
                    text_val = section.get("extracted_text", "")
                    if text_val:
                        st.caption(text_val[:150] + "..." if len(text_val) > 150 else text_val)
                    if section.get("ai_description"):
                        st.info(section["ai_description"])
        else:
            st.info("구조 분석 데이터가 없습니다. AI 파이프라인 실행 후 확인하세요.")

    # --- 소구점 키워드 차트 ---
    with col_right:
        st.subheader("소구점 키워드 TOP 20")
        tags = detail.get("tags", [])
        if tags:
            df = pd.DataFrame({"keyword": tags, "count": [1] * len(tags)})
            fig = px.bar(
                df.head(20),
                x="count", y="keyword",
                orientation="h",
                color_discrete_sequence=["#FF6B6B"],
                title=f"{selected_label.split(' - ')[0]} 주요 키워드",
            )
            fig.update_layout(
                yaxis={"categoryorder": "total ascending"},
                showlegend=False,
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("키워드 데이터가 없습니다.")

        st.markdown("---")
        product_url = next((p["product_url"] for p in products if p["id"] == selected_id), None)
        if product_url:
            st.markdown(f"[올리브영 원본 페이지 열기]({product_url})")
