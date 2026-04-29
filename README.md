# K-Beauty 레퍼런스 수집 및 분석 시스템

닥터코리아(Dr. Korea) 내부용 — 올리브영 상품 데이터를 자동 수집·AI 분석하여 PM/디자이너/COO가 마케팅 레퍼런스를 탐색하는 Streamlit 대시보드입니다.

---

## 시스템 구조

```
크롤러(Playwright) → Google Drive(이미지) + PostgreSQL(메타데이터)
                                    ↓
              FastAPI 백엔드 → Streamlit 대시보드 (팀원 접속)
                                    ↓
            AI 파이프라인: GPT-4o Vision(구조 태깅) + CLIP(이미지 벡터화)
```

---

## 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론 후
cp .env.example .env
# .env 파일을 열어 각 값을 채워넣으세요
```

### 2. Google Drive Service Account 설정

1. [Google Cloud Console](https://console.cloud.google.com/) → 새 프로젝트 생성
2. **Google Drive API** 활성화
3. **서비스 계정 생성** → JSON 키 다운로드
4. 다운로드한 JSON 파일을 `credentials/google_service_account.json`에 저장
5. 본인 Google Drive에서 루트 폴더 생성 → 폴더 ID를 `.env`의 `GOOGLE_DRIVE_ROOT_FOLDER_ID`에 입력
6. 해당 폴더를 서비스 계정 이메일과 공유 (편집자 권한)

### 3. Docker로 실행 (권장)

```bash
docker-compose up -d
```

- DB 초기화: `docker-compose exec backend python -m database.init_db`
- FastAPI 문서: http://localhost:8000/docs
- Streamlit 대시보드: http://localhost:8501

### 4. 로컬 직접 실행

```bash
pip install -r requirements.txt
playwright install chromium

# DB 초기화 (PostgreSQL이 실행 중이어야 함)
python -m database.init_db

# FastAPI 서버 실행
uvicorn backend.main:app --reload

# Streamlit 대시보드 실행 (새 터미널)
streamlit run dashboard/app.py

# 스케줄러 실행 (새 터미널)
python scheduler.py

# 즉시 크롤링 테스트
python scheduler.py --run-now
```

---

## 크롤링 스케줄

- **시작**: 매주 금요일 18:00 KST
- **완료 목표**: 토요일 09:00 KST
- **수집 범위**: 올리브영 10개 카테고리 × 인기순 Top 30 = 최대 300개 상품/주

---

## 대시보드 모드

| 모드 | 대상 | 주요 기능 |
|---|---|---|
| PM 뷰 | 기획자 | 상세 페이지 구조 타임라인, 소구점 키워드 차트 |
| 디자이너 뷰 | 디자이너 | Pinterest형 갤러리, AI 유사 이미지 검색 |
| COO 뷰 | 전략가 | 주간 트렌드 급상승 Top10, 카테고리 현황, 경쟁 브랜드 분석 |

---

## Streamlit Community Cloud 배포

1. GitHub에 이 저장소 업로드 (`.env`, `credentials/` 제외)
2. [share.streamlit.io](https://share.streamlit.io) 접속
3. **New app** → 저장소 연결 → Main file: `dashboard/app.py`
4. **Secrets** 탭에서 `.streamlit/secrets.toml.example` 내용 입력
5. Deploy 클릭

---

## 주의사항

- 수집된 데이터는 **내부 기획·디자인 레퍼런스 용도로만** 사용할 것 (저작권 준수)
- `.env` 파일과 `credentials/` 폴더는 **절대 git에 커밋하지 말 것**
- Google Drive 무료 15GB 용량 초과 시 오래된 폴더 수동 정리 필요
