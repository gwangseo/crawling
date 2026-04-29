## 5. 백엔드 시스템 설계 (Backend API System - FastAPI)

프론트엔드 대시보드(Streamlit)와 크롤러/DB 간의 데이터 통신을 담당할 RESTful API를 FastAPI로 구축한다.

### 5.1. 주요 API 엔드포인트 명세
* `GET /api/v1/products`: 카테고리, 텍스트 키워드를 입력받아 DB에서 상품 리스트를 반환. (페이지네이션 적용)
* `GET /api/v1/products/{product_id}/assets`: 특정 상품의 Google Drive 에셋 링크(Thumbnail, GIF, Detail Image 등)를 반환.
* `GET /api/v1/trends/top-liked`: 이번 주 찜(좋아요) 수 및 리뷰 수가 가장 많이 급증한 상품 Top 10을 시계열 데이터(`product_metrics`) 기반으로 계산하여 반환.
* `POST /api/v1/search/visual-similar`: 디자이너가 업로드한 이미지나 선택한 에셋의 Vector 값을 기준으로, `pgvector`를 활용해 코사인 유사도(Cosine Similarity)가 가장 높은 타 상품의 에셋들을 반환.

### 5.2. 백엔드 아키텍처 규칙
* **의존성 주입(Dependency Injection):** DB 세션은 FastAPI의 `Depends`를 사용하여 관리한다.
* **비동기 처리(Async):** DB I/O 속도 향상을 위해 `asyncpg` 등 비동기 드라이버를 권장하나, 안정성이 우선이라면 동기식 `psycopg2`를 사용해도 무방하다.

---

## 6. 예외 처리 및 모니터링 시스템 (Error Handling & Monitoring)

크롤링 파이프라인과 서버의 안정적인 운영을 위한 모니터링 체계를 구축한다.

### 6.1. 로깅 및 알림 로직 (Slack Webhook)
* **에러 레벨 관리:** 단순 타임아웃(`Warning`)과 DOM 구조 변경에 의한 셀렉터 에러(`Critical`)를 분리하여 로깅한다.
* **Slack 알림:** `Critical` 에러 발생 시, 또는 매주 토요일 오전 크롤링 작업이 성공적으로 종료되었을 때 (수집된 총 상품 수, 신규 추가 에셋 수, 에러율 등) 요약 리포트를 Slack Webhook API를 통해 전송하는 파이썬 모듈을 작성한다.

### 6.2. Google Drive API 예외 처리
* API 일일 쿼리 한도(Quota) 초과 시 `429 Too Many Requests` 에러를 캐치하고, `Exponential Backoff` 로직을 적용하여 일정 시간 대기 후 재시도하도록 구성한다.