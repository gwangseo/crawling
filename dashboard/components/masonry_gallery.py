"""
Pinterest 스타일 Masonry 갤러리 컴포넌트
st.columns를 활용한 타일 레이아웃
"""
import re
import streamlit as st
from typing import Optional


def _to_displayable_url(url: str) -> str:
    """
    Google Drive uc?export=view URL → thumbnail URL 변환
    (uc?export=view는 2023년 이후 신뢰도 낮음, thumbnail 엔드포인트가 안정적)
    """
    if not url:
        return url
    # https://drive.google.com/uc?export=view&id=FILE_ID
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if match and "drive.google.com" in url:
        file_id = match.group(1)
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"
    return url


def render_masonry_gallery(
    assets: list[dict],
    cols: int = 4,
    show_caption: bool = True,
    on_select_callback=None,
):
    """
    assets: [{"drive_url": str, "asset_type": str, "brand": str, "product_name": str, "id": str}]
    """
    if not assets:
        st.info("표시할 에셋이 없습니다.")
        return

    columns = st.columns(cols)
    for i, asset in enumerate(assets):
        col = columns[i % cols]
        with col:
            drive_url = _to_displayable_url(asset.get("drive_url", ""))
            if not drive_url:
                continue

            try:
                st.image(
                    drive_url,
                    use_column_width=True,
                    caption=f"{asset.get('brand', '')} - {asset.get('product_name', '')}" if show_caption else None,
                )

                # GIF 배지
                if asset.get("asset_type") == "gif":
                    st.markdown('<span style="color:#FF6B6B;font-size:11px;font-weight:bold;">GIF</span>', unsafe_allow_html=True)

                if on_select_callback:
                    btn_key = f"select_{asset.get('id', i)}"
                    if st.button("비슷한 무드 찾기", key=btn_key, use_container_width=True):
                        on_select_callback(asset)
            except Exception:
                st.warning("이미지 로드 실패")


def render_image_grid(
    items: list[dict],
    image_key: str = "drive_url",
    label_key: str = "name",
    cols: int = 3,
):
    """단순 그리드 레이아웃 (상품 목록용)"""
    if not items:
        st.info("데이터가 없습니다.")
        return

    for i in range(0, len(items), cols):
        row_items = items[i:i+cols]
        columns = st.columns(len(row_items))
        for col, item in zip(columns, row_items):
            with col:
                if item.get(image_key):
                    st.image(item[image_key], use_column_width=True)
                st.caption(item.get(label_key, ""))
