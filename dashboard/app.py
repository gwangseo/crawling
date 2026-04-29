"""
Streamlit 대시보드 진입점
사이드바에서 3가지 모드 선택:
- Mode 1: 기획자(PM) 뷰
- Mode 2: 디자이너 뷰
- Mode 3: 전략가(COO) 뷰
"""
import os
import sys

# Streamlit Cloud는 dashboard/app.py가 있는 폴더를 기준으로 실행하기 때문에
# 프로젝트 루트(/mount/src/crawling/)를 sys.path에 수동으로 추가해야
# `from dashboard.xxx import ...` 같은 절대 임포트가 동작한다.
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

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


def _trigger_crawl():
    """GitHub Actions workflow_dispatch API를 호출하여 크롤링 트리거"""
    import urllib.request
    import json as _json

    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPO", "")  # 예: "username/crawling"

    if not token or not repo:
        st.error("GITHUB_TOKEN 또는 GITHUB_REPO 시크릿이 설정되지 않았습니다.")
        return

    url = f"https://api.github.com/repos/{repo}/actions/workflows/weekly_crawl.yml/dispatches"
    payload = _json.dumps({"ref": "main"}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                st.success("크롤링 시작됨! GitHub Actions에서 진행 상황을 확인하세요.")
            else:
                st.warning(f"응답 코드: {resp.status}")
    except Exception as e:
        st.error(f"크롤링 트리거 실패: {e}")


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

        # 관리자 전용 패널
        with st.expander("🔒 관리자"):
            pw = st.text_input("관리자 암호", type="password", key="admin_pw")
            admin_password = os.environ.get("ADMIN_PASSWORD", "")
            if pw and pw == admin_password:
                st.success("인증됨")
                if st.button("지금 크롤링 실행", type="primary", key="trigger_crawl"):
                    _trigger_crawl()
            elif pw:
                st.error("암호가 틀렸습니다.")

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
