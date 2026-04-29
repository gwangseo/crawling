"""
Google Drive API 연동 모듈
- OAuth2 사용자 인증 (서비스 계정 대신 사용자 본인 계정의 Drive 용량 사용)
- 카테고리/브랜드/상품 폴더 자동 생성
- 파일 업로드 및 공개 URL 반환
"""
import os
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import logging as _logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_PATH = Path("credentials/token.json")
CLIENT_SECRET_PATH = Path("credentials/oauth_client.json")


def _get_root_folder_id() -> str:
    return os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "")


def get_drive_service():
    """
    OAuth2 사용자 인증으로 Google Drive API 서비스 객체 반환.
    credentials/token.json 이 없으면 auth_drive.py 를 먼저 실행해야 한다.
    """
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(
            f"Drive 인증 토큰이 없습니다. 먼저 `python auth_drive.py` 를 실행하세요. "
            f"(찾는 경로: {TOKEN_PATH.resolve()})"
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            logger.debug("[Drive] 토큰 갱신 중...")
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError(
                "Drive 인증 토큰이 만료되었습니다. `python auth_drive.py` 를 다시 실행하세요."
            )

    return build("drive", "v3", credentials=creds)


def get_or_create_folder(service, parent_id: str, folder_name: str) -> str:
    """Drive에서 폴더를 찾거나 없으면 생성한다. 반환: 폴더 ID"""
    query = (
        f"name='{folder_name}' and "
        f"'{parent_id}' in parents and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"trashed=false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    logger.debug(f"[Drive] 폴더 생성: {folder_name}")
    return folder["id"]


def ensure_product_folder(service, category: str, brand: str, product_name: str) -> str:
    """K-Beauty_Assets / {category} / {brand} / {product_name} 폴더 구조 자동 생성"""
    def sanitize(name: str) -> str:
        return name.replace("/", "_").replace("\\", "_").strip()[:100]

    root_id = _get_root_folder_id()
    if not root_id:
        raise ValueError("GOOGLE_DRIVE_ROOT_FOLDER_ID 환경변수가 설정되지 않았습니다.")
    category_id = get_or_create_folder(service, root_id, sanitize(category))
    brand_id = get_or_create_folder(service, category_id, sanitize(brand))
    product_id = get_or_create_folder(service, brand_id, sanitize(product_name))
    return product_id


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    before_sleep=before_sleep_log(_logging.getLogger("drive_retry"), _logging.WARNING),
    reraise=True,
)
def upload_file_to_drive(service, local_path: str, folder_id: str, filename: str) -> dict:
    """파일을 Drive에 업로드하고 공개 링크를 반환한다."""
    mime_type = _get_mime_type(filename)
    metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink",
    ).execute()

    file_id = uploaded["id"]

    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    drive_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"
    web_view_link = uploaded.get("webViewLink", "")

    logger.info(f"[Drive] 업로드 완료: {filename} → {drive_url}")
    return {"file_id": file_id, "drive_url": drive_url, "web_view_link": web_view_link}


def _get_mime_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }
    return mime_map.get(ext, "application/octet-stream")


def upload_product_assets(
    category: str,
    brand: str,
    product_name: str,
    assets: list[dict],
) -> list[dict]:
    """
    상품의 모든 에셋을 Drive에 업로드한다.
    assets: [{"local_path": str, "asset_type": str, "filename": str}]
    반환: [{"asset_type": str, "file_id": str, "drive_url": str}]
    """
    service = get_drive_service()
    folder_id = ensure_product_folder(service, category, brand, product_name)

    results = []
    for asset in assets:
        if not asset.get("local_path") or not os.path.exists(asset["local_path"]):
            continue
        try:
            upload_result = upload_file_to_drive(
                service,
                local_path=asset["local_path"],
                folder_id=folder_id,
                filename=asset["filename"],
            )
            results.append({
                "asset_type": asset["asset_type"],
                "file_id": upload_result["file_id"],
                "drive_url": upload_result["drive_url"],
                "original_filename": asset["filename"],
            })
        except Exception as e:
            logger.error(f"[Drive] 업로드 실패 - {asset['filename']}: {e}")

    return results
