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


def _dispatch_workflow(workflow_file: str, inputs: dict = None):
    """GitHub Actions workflow_dispatch API 공통 호출"""
    import urllib.request
    import json as _json

    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPO", "")

    if not token or not repo:
        st.error("GITHUB_TOKEN 또는 GITHUB_REPO 시크릿이 설정되지 않았습니다.")
        return False

    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/dispatches"
    body = {"ref": "main"}
    if inputs:
        body["inputs"] = inputs

    payload = _json.dumps(body).encode()
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
            return resp.status == 204
    except Exception as e:
        st.error(f"GitHub Actions 트리거 실패: {e}")
        return False


def _trigger_crawl():
    if _dispatch_workflow("weekly_crawl.yml"):
        st.success("크롤링 시작됨! GitHub Actions 탭에서 진행 상황을 확인하세요.")


def _trigger_reanalyze(limit: int, force: bool):
    inputs = {"limit": str(limit), "force": "true" if force else "false"}
    if _dispatch_workflow("reanalyze_ai.yml", inputs):
        mode = "전체 재분석" if force else "미분석 상품 분석"
        st.success(f"AI {mode} 시작됨! 상품 {limit}개 처리 예정. GitHub Actions에서 진행 확인.")


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

                st.markdown("**크롤링**")
                if st.button("지금 크롤링 실행", type="primary", key="trigger_crawl"):
                    _trigger_crawl()

                st.markdown("---")
                st.markdown("**AI 분석**")

                ai_limit = st.number_input(
                    "분석할 상품 수", min_value=1, max_value=200,
                    value=20, step=10, key="ai_limit"
                )
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("미분석 상품 AI 분석", key="reanalyze_new"):
                        _trigger_reanalyze(int(ai_limit), force=False)
                with col_b:
                    if st.button("전체 AI 재분석 (덮어씌우기)", key="reanalyze_force",
                                 type="secondary"):
                        _trigger_reanalyze(int(ai_limit), force=True)

                st.caption("미분석: 레이아웃 데이터 없는 상품만  |  전체: 기존 분석 결과 삭제 후 재실행")
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
