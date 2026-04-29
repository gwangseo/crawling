## 3. 데이터베이스 및 스토리지 아키텍처 (DB & Storage Architecture)

고용량 미디어 파일 처리로 인한 비용을 최적화하기 위해 AWS S3 대신 **Google Drive API**를 스토리지로 사용하고, 메타 데이터와 벡터 임베딩은 **PostgreSQL(pgvector)**에 저장하는 하이브리드 구조를 구축한다.

### 3.1. Google Drive 연동 및 폴더 구조 (Storage)
* **인증 방식:** Google Cloud Console에서 생성한 Service Account(JSON 키)를 사용하여 서버에서 API로 접근한다.
* **디렉토리 아키텍처:** 크롤러가 에셋을 다운로드하면, 드라이브 내에 자동으로 아래와 같은 계층 구조의 폴더를 생성하고 파일을 업로드해야 한다.
  * `[Root Folder]` > `[Category Name]` > `[Brand Name]` > `[Product Name]`
  * 예시: `K-Beauty_Assets / 스킨케어 / 라운드랩 / 자작나무 수분 선크림 / thumbnail.jpg`
* **파일 공유 권한:** 업로드된 파일은 서비스 계정 권한에서 "링크가 있는 모든 사용자(읽기)" 권한으로 변경한 뒤, 웹에서 바로 접근/렌더링할 수 있는 `webContentLink` 또는 `webViewLink`를 추출하여 DB에 반환해야 한다.

### 3.2. PostgreSQL 스키마 설계 (SQLAlchemy ORM 기준)
데이터베이스는 시계열 트렌드 분석과 AI 벡터 검색이 가능하도록 정규화한다. 아래 테이블 구조를 참고하여 ORM 모델을 작성하라.

* **`products` (상품 마스터):**
  * `id` (PK, UUID), `oliveyoung_id` (Unique)
  * `brand`, `name`, `category`
  * `original_price`, `discount_price`
  * `created_at`, `updated_at`
* **`product_metrics` (주간 트렌드 추적용 시계열 테이블):**
  * `id` (PK), `product_id` (FK)
  * `likes_count` (찜 수), `review_count` (리뷰 수), `rating` (평점)
  * `captured_at` (수집 일시) -> COO의 '찜 수 급상승 브랜드' 대시보드 구현을 위한 핵심 데이터.
* **`assets` (시각 에셋 테이블):**
  * `id` (PK), `product_id` (FK)
  * `asset_type` (Enum: 'thumbnail', 'detail_image', 'gif', 'video')
  * `drive_file_id`, `drive_url` (Google Drive 직접 링크)
  * `visual_embedding` (Vector 타입, pgvector 사용, 향후 AI가 생성한 이미지 임베딩 값 저장)
* **`product_layouts` (PM 상세페이지 구조화 테이블):**
  * `id` (PK), `product_id` (FK)
  * `section_order` (Integer, 상단부터 순서)
  * `section_category` (Enum: Hook, Problem, Solution, Proof, How-to 등 AI가 태깅한 구조)
  * `extracted_text` (OCR로 추출한 텍스트)
* **`tags` (키워드/해시태그 테이블):**
  * `id`, `product_id`, `keyword`

---

## 4. 수집 주기 및 크롤러 부하 분산 전략 (Crawler Load Balancing & Scheduling)

올리브영의 Anti-Bot 시스템을 우회하고, 서버 자원을 효율적으로 사용하기 위해 크롤러는 철저한 '저속 분산(Low-Speed Distributed)' 방식으로 동작해야 한다.

### 4.1. 스케줄링 정책 (Batch Schedule)
* **목표 수집 완료 시간:** 매주 토요일 오전 09:00.
* **시작 시간:** 매주 금요일 18:00 (APScheduler 또는 Celery Beat를 사용하여 Cron Job 설정).
* 금요일 저녁부터 토요일 아침까지 약 15시간 동안 천천히 수집 사이클을 돌린다.

### 4.2. 안티 크롤링(Anti-Bot) 방어 로직 (필수 구현)
* **Random Sleep:** 페이지 간 이동 시 `random.uniform(3.5, 8.2)` 초 수준의 무작위 지연 시간을 반드시 적용한다.
* **User-Agent & Headers Rotation:** 최신 데스크톱 브라우저(Chrome, Safari, Edge)의 User-Agent 리스트를 순회하며 요청 헤더를 구성한다.
* **Playwright Stealth:** Playwright 구동 시 `playwright-stealth` 패키지를 적용하여 `navigator.webdriver`를 `false`로 우회하는 등 자동화 봇 탐지 필터를 회피한다.

### 4.3. 중복 처리 및 상태 관리 (Idempotency & Resiliency)
* **이어하기 기능(State Checkpoint):** 크롤러가 모종의 이유(네트워크 에러, IP 임시 차단 등)로 중간에 중단되었을 경우, 재시작 시 이미 수집이 완료된 `product_id`는 건너뛰고 다음 상품부터 진행하는 체크포인트 로직(SQLite 또는 메모리 캐시 활용)을 구현한다.
* **DB Update 분기 로직 (중복 다운로드 방지):**
  * 이번 주에 수집하려는 상품이 이미 `products` 테이블에 존재한다면?
  * -> 상품 사진(Assets)을 다시 다운로드하여 Google Drive 용량을 낭비하지 않는다.
  * -> 대신 `product_metrics` 테이블에 새로운 row(이번 주의 찜 수, 리뷰 수)만 `INSERT` 하여 트렌드 변화만 추적한다.
* **에러 핸들링 로직:** 특정 상품 페이지 구조가 달라 크롤링 중 `Timeout` 또는 `SelectorNotFound` 에러가 발생하면, 해당 상품만 Skip(로그 기록)하고 전체 파이프라인이 멈추지 않도록 `try-except` 블록으로 격리한다.