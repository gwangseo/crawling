"""
Mode 3: 전략가(COO) 뷰
- 주간 찜 수 / 리뷰 급상승 Top 10 트렌드 테이블
- 카테고리별 요약 현황
- 경쟁 브랜드 검색
"""
import streamlit as st
import plotly.express as px
import pandas as pd


def render():
    st.header("전략가(COO) 뷰 — 트렌드 분석 & 시장 포지셔닝")

    # ===== 섹션 1: 주간 급상승 TOP 10 =====
    st.subheader("이번 주 찜 수 급상승 Top 10")
    st.caption("전주 대비 찜(좋아요) 증가량 기준 정렬 — 빠르게 바이럴되는 인디 브랜드 발굴에 활용하세요.")

    try:
        from dashboard.db import get_top_liked_products
        trends = get_top_liked_products(limit=10)

        if trends:
            df = pd.DataFrame(trends)
            df["증감"] = df["likes_delta"].apply(lambda x: f"+{x:,}" if x > 0 else str(x))
            df["등급"] = df["likes_delta"].apply(_classify_trend)

            display_df = df[[
                "brand", "name", "category",
                "current_likes", "prev_likes", "증감",
                "current_reviews", "rating", "등급"
            ]].rename(columns={
                "brand": "브랜드",
                "name": "상품명",
                "category": "카테고리",
                "current_likes": "현재 찜 수",
                "prev_likes": "전주 찜 수",
                "current_reviews": "리뷰 수",
                "rating": "평점",
            })

            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "증감": st.column_config.TextColumn("찜 증감", help="전주 대비 찜 수 변화"),
                    "등급": st.column_config.TextColumn("트렌드"),
                    "현재 찜 수": st.column_config.NumberColumn(format="%d"),
                    "전주 찜 수": st.column_config.NumberColumn(format="%d"),
                },
            )

            fig = px.bar(
                df.head(10),
                x="brand",
                y="likes_delta",
                color="category",
                title="찜 수 급상승 브랜드 (전주 대비)",
                labels={"brand": "브랜드", "likes_delta": "찜 증가량", "category": "카테고리"},
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("트렌드 데이터가 없습니다. 최소 2회 이상 크롤링 후 확인하세요.")
    except Exception as e:
        st.error(f"트렌드 데이터 로드 실패: {e}")

    st.divider()

    # ===== 섹션 2: 카테고리별 현황 =====
    st.subheader("카테고리별 현황 요약")
    try:
        from dashboard.db import get_category_summary
        cat_data = get_category_summary()

        if cat_data:
            cat_df = pd.DataFrame(cat_data).rename(columns={
                "category": "카테고리",
                "product_count": "상품 수",
                "avg_likes": "평균 찜 수",
                "avg_reviews": "평균 리뷰 수",
                "avg_rating": "평균 평점",
            })

            col1, col2 = st.columns([1, 1])
            with col1:
                st.dataframe(cat_df, use_container_width=True)
            with col2:
                fig2 = px.pie(
                    cat_df,
                    values="상품 수",
                    names="카테고리",
                    title="카테고리별 수집 상품 비율",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("카테고리 데이터가 없습니다.")
    except Exception as e:
        st.error(f"카테고리 현황 로드 실패: {e}")

    st.divider()

    # ===== 섹션 3: 경쟁 브랜드 분석 =====
    st.subheader("경쟁 브랜드 클러스터 분석")
    st.caption("분석하고 싶은 브랜드명 또는 상품명을 입력하면 유사한 인디 브랜드 리스트를 보여줍니다.")

    target_keyword = st.text_input("타겟 브랜드/상품 검색", placeholder="예: 라운드랩, 조선미녀...", key="coo_target")

    if target_keyword:
        try:
            from dashboard.db import search_products
            results = search_products(keyword=target_keyword, limit=50)

            if results:
                result_df = pd.DataFrame(results).rename(columns={
                    "brand": "브랜드",
                    "name": "상품명",
                    "category": "카테고리",
                    "original_price": "정가",
                    "discount_price": "할인가",
                })
                st.dataframe(
                    result_df[["브랜드", "상품명", "카테고리", "정가", "할인가"]],
                    use_container_width=True,
                )
                st.caption(f"'{target_keyword}' 관련 {len(results)}개 상품 발견")
            else:
                st.info(f"'{target_keyword}'에 해당하는 상품이 없습니다.")
        except Exception as e:
            st.error(f"검색 실패: {e}")


def _classify_trend(delta: int) -> str:
    if delta >= 500:
        return "급상승"
    elif delta >= 100:
        return "상승"
    elif delta >= 0:
        return "유지"
    else:
        return "하락"
