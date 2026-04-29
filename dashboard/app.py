"""
Streamlit 대시보드 진입점
사이드바에서 3가지 모드 선택:
- Mode 1: 기획자(PM) 뷰
- Mode 2: 디자이너 뷰
- Mode 3: 전략가(COO) 뷰
"""
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Streamlit Community Cloud: secrets → 환경변수 주입
# (database/session.py가 os.getenv("DB_URL")로 읽기 때문에 필요)
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

st.set_page_config(
    page_title="K-Beauty 레퍼런스 DB | 닥터코리아",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 스타일 커스터마이징
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #1a1a2e;
    }
    [data-testid="stSidebar"] * {
        color: #eee;
    }
    .main-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #FF6B6B;
        margin-bottom: 0;
    }
    .sub-title {
        font-size: 0.9rem;
        color: #888;
        margin-top: 0;
    }
    .stButton > button {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown('<p class="main-title">닥터코리아</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-title">K-Beauty 레퍼런스 분석 시스템</p>', unsafe_allow_html=True)
        st.divider()

        mode = st.radio(
            "모드 선택",
            options=["PM — 구조 & 카피 분석", "디자이너 — 비주얼 레퍼런스", "COO — 트렌드 & 전략"],
            key="mode_select",
        )

        st.divider()
        st.caption("데이터 출처: 올리브영")
        st.caption("수집 주기: 매주 금요일 18:00")

        # 수동 크롤링 트리거 (관리자용)
        with st.expander("관리자 기능"):
            if st.button("지금 크롤링 실행", type="secondary"):
                st.warning("이 기능은 scheduler.py --run-now 로 실행해주세요.")

    return mode


def main():
    mode = render_sidebar()

    if mode == "PM — 구조 & 카피 분석":
        from dashboard.views.pm_view import render
        render()

    elif mode == "디자이너 — 비주얼 레퍼런스":
        from dashboard.views.designer_view import render
        render()

    elif mode == "COO — 트렌드 & 전략":
        from dashboard.views.coo_view import render
        render()


if __name__ == "__main__":
    main()
