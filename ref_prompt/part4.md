## 7. 팀원별 실무 활용 시나리오 및 대시보드 UI (Streamlit UI/UX)

Streamlit을 사용하여 사내 팀원들이 접근할 하이브리드 대시보드를 구축한다. 사이드바(Sidebar)를 통해 3가지 모드(Mode)를 제공한다.

### 7.1. Mode 1: 기획자(PM) 뷰 - 구조 및 패턴 분석
* **UI 레이아웃:** 카테고리 선택 후, 타겟 상품을 고르면 해당 상품의 '상세 페이지 구조 타임라인(예: Hook -> Problem -> Solution)'을 블록 형태로 시각화한다.
* **키워드 클라우드:** 해당 카테고리에서 AI가 추출한 핵심 소구점 키워드(텍스트)들의 빈도수를 워드 클라우드나 바 차트로 렌더링한다.

### 7.2. Mode 2: 디자이너 뷰 - 시각적 무드 레퍼런스
* **UI 레이아웃:** 핀터레스트(Pinterest) 형태의 Masonry 갤러리 뷰. 이미지와 GIF만 타일 형태로 렌더링한다.
* **유사도 검색 기능:** 특정 이미지를 클릭하고 "이와 비슷한 무드 찾기" 버튼을 누르면, 백엔드의 `/api/v1/search/visual-similar` 엔드포인트를 호출하여 유사한 에셋들을 즉시 불러온다.

### 7.3. Mode 3: 전략가(COO) 뷰 - 경쟁사 포지셔닝 및 트렌드
* **UI 레이아웃:** 데이터 테이블(DataFrame) 중심. 주간 찜 수 급상승률, 리뷰 급증률을 기준으로 정렬 가능한 표를 제공한다.
* **경쟁사 클러스터링:** 타겟 브랜드명을 입력하면, 카테고리 및 가격대가 유사한 경쟁 인디 브랜드 리스트와 그들의 반응도(리뷰 평점)를 보여준다.

---

## 8. AI 기반의 데이터 가공 (AI Processing & pgvector)

크롤링 직후 수집된 텍스트와 이미지를 '실질적인 무기'로 바꾸기 위해 AI를 활용한 데이터 가공 파이프라인을 구축한다.

### 8.1. 시각 에셋 분해 및 태깅 (OpenAI Vision API)
* 크롤러가 상세 페이지의 긴 통이미지(또는 썸네일)를 수집하면, 이를 OpenAI `gpt-4o` API (Vision)에 전송한다.
* **프롬프트 지시:** "이 뷰티 상세페이지 이미지를 분석하여, 시각적 무드(예: 미니멀, 화려함, 친환경 등)와 페이지 구조(Hook, 성분 강조, 리뷰 증명 등)를 JSON 형태로 태깅해 반환하라."
* 반환된 텍스트/태그를 `product_layouts` 및 `tags` 테이블에 적재한다.

### 8.2. 이미지 벡터화 (Embedding)
* 수집된 개별 에셋(이미지)들을 CLIP 모델이나 OpenAI의 멀티모달 임베딩 API에 통과시켜 n차원 벡터 데이터로 변환한다.
* 변환된 값을 PostgreSQL의 `assets.visual_embedding` 필드(Vector 타입)에 저장하여 이후 Streamlit에서 유사도 검색 시 활용할 수 있도록 한다.

---

## 9. 인프라 구축 및 배포 환경 (Infrastructure & Deployment)

로컬 개발 환경과 실제 운영(클라우드) 환경을 통일하고, 누구나 쉽게 실행할 수 있도록 컨테이너화한다.

### 9.1. Docker 및 Docker Compose
* `docker-compose.yml`을 작성하여 다음 3개의 컨테이너를 하나로 묶는다.
  1. **Backend (FastAPI + Crawler + AI Processor):** Python 3.10 컨테이너 (Playwright 실행을 위한 브라우저 바이너리 포함).
  2. **Frontend (Streamlit):** 내부 포트 8501 노출.
  3. **Database (PostgreSQL + pgvector):** 공식 pgvector 도커 이미지 사용.

### 9.2. 환경 변수 및 보안 (.env)
* 절대로 코드 내에 하드코딩하지 않아야 할 정보들:
  * `DB_URL` (PostgreSQL 접속 정보)
  * `OPENAI_API_KEY` (AI 태깅 및 임베딩용)
  * `GOOGLE_APPLICATION_CREDENTIALS` (Google Drive Service Account JSON 경로)
  * `SLACK_WEBHOOK_URL`

### 🎯 첫 번째 미션 지시 (Action Item for the AI)
이상의 문서를 모두 숙지했다면, "이해 완료"라고 짧게 대답한 후 **가장 첫 번째 작업으로 PostgreSQL DB 스키마(`models.py` 파일) 작성과, 크롤러가 Google Drive에 폴더를 만들고 사진을 업로드하는 기초 함수(`drive_utils.py`) 코드**를 작성해 줘.