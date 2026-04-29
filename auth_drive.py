"""
Google Drive OAuth2 최초 인증 스크립트
- 한 번만 실행하면 credentials/token.json 이 생성됩니다.
- 이후 크롤러는 이 토큰을 자동으로 갱신하며 사용합니다.

사용법:
    python auth_drive.py
"""
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]
CLIENT_SECRET_PATH = Path("credentials/oauth_client.json")
TOKEN_PATH = Path("credentials/token.json")


def main():
    if not CLIENT_SECRET_PATH.exists():
        print(f"[오류] OAuth 클라이언트 시크릿 파일이 없습니다: {CLIENT_SECRET_PATH.resolve()}")
        print()
        print("GCP Console에서 다음 단계를 수행하세요:")
        print("  1. https://console.cloud.google.com/ → kbeauty-crawler 프로젝트")
        print("  2. API 및 서비스 > 사용자 인증 정보")
        print("  3. 사용자 인증 정보 만들기 > OAuth 클라이언트 ID")
        print("  4. 애플리케이션 유형: 데스크톱 앱")
        print("  5. JSON 다운로드 → credentials/oauth_client.json 으로 저장")
        return

    print("[Drive 인증] 브라우저가 열리면 Google 계정으로 로그인하세요.")
    print("(Drive 폴더 K-Beauty_Assets 가 있는 계정으로 로그인)")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    print(f"\n[완료] 인증 토큰 저장됨: {TOKEN_PATH.resolve()}")
    print("이제 python scheduler.py --run-now 로 크롤러를 실행할 수 있습니다.")


if __name__ == "__main__":
    main()
