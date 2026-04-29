"""
Gemini Vision을 사용한 K-뷰티 상세 페이지 구조 태깅 + 키워드 추출
"""
import os
import json
from typing import Optional
from loguru import logger

import google.generativeai as genai
from PIL import Image

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

# ─────────────────────────────────────────────────────────────
# 프롬프트 1: 상세 이미지 구조 분석 (Gemini Vision)
# ─────────────────────────────────────────────────────────────
LAYOUT_TAGGING_PROMPT = """
당신은 K-뷰티 마케팅 전략 전문가입니다.
아래 뷰티 제품 상세 페이지 이미지들(순서대로 위→아래)을 분석하여, 각 섹션의 마케팅 구조를 분류하세요.

[섹션 분류 기준]
- Hook       : 브랜드/제품명 소개, 강렬한 핵심 카피, 감성 무드 이미지. 고객의 시선을 첫 3초 안에 잡는 영역.
- Problem    : 소비자의 피부 고민·불편함 언급 (예: 건조함, 잡티, 모공, 피부 트러블, 칙칙함).
- Solution   : 제품이 어떻게 그 고민을 해결하는지 설명 — 핵심 성분, 특허 기술, 작용 메커니즘 강조.
- Proof      : 신뢰도 증거 — 임상 시험 결과(%), 전후 사진(Before/After), 수상 이력, 전문가 추천, 소비자 후기.
- How-to     : 제품 사용법, 적정 사용량, 사용 순서(루틴).
- Ingredient : 성분 상세 설명 — 원료 출처, 함량, 복합 성분 시너지.
- Other      : 위 분류에 해당하지 않는 브랜드 스토리, 패키징 설명, CSR 등.

[출력 규칙]
- 반드시 아래 JSON 형식만 출력하세요. 설명이나 마크다운 코드블록 없이 JSON만.
- sections 배열은 이미지 순서(위→아래)를 따릅니다.
- extracted_text는 이미지에서 실제로 읽히는 한국어/영어 텍스트를 그대로 옮겨 적으세요 (없으면 "").
- description은 이 섹션이 전달하는 마케팅 메시지를 1-2줄로 요약하세요.

{
  "sections": [
    {
      "order": 1,
      "category": "Hook",
      "extracted_text": "이미지에서 읽히는 텍스트",
      "description": "이 섹션의 마케팅 의도 요약"
    }
  ],
  "overall_mood": "전체 상세 페이지의 시각적 무드 (예: 미니멀 클린, 럭셔리, 자연친화, 활기찬, 감성적)",
  "color_palette": "주조 색상 3가지 (예: 아이보리, 딥그린, 골드)",
  "target_audience": "이 상세 페이지가 타겟하는 소비자 페르소나 추정 (예: 20대 민감성 피부 직장인)"
}
"""

# ─────────────────────────────────────────────────────────────
# 프롬프트 2: 텍스트 기반 키워드 + 소구점 추출 (Gemini Text)
# ─────────────────────────────────────────────────────────────
KEYWORD_EXTRACTION_PROMPT = """
당신은 K-뷰티 마케팅 카피라이터입니다.
아래 뷰티 제품 정보를 읽고, 실제 마케팅 기획에 바로 활용할 수 있는 키워드를 추출하세요.

[제품 정보]
브랜드: {brand}
제품명: {product_name}
설명 텍스트: {description}
페이지 해시태그: {hashtags}

[추출 기준]
1. 피부 효능 키워드: 실제 효과 클레임 (예: 수분광, 톤업, 모공축소, 진정)
2. 핵심 성분 키워드: 언급된 유효 성분 (예: 히알루론산, 나이아신아마이드, 판테놀)
3. 피부 타입 키워드: 타겟 피부 고민 (예: 건성, 민감성, 지성, 복합성)
4. 마케팅 소구점: 경쟁 우위를 나타내는 문구 (예: 피부과 테스트 완료, 비건, 무향)
5. 감성/라이프스타일 키워드: 브랜드 무드 (예: 데일리케어, 아침루틴, 저자극)

[출력 규칙]
- 반드시 아래 JSON 형식만 출력. 마크다운 코드블록 없이 JSON만.
- 각 키워드는 10자 이내의 짧은 단어/구문으로.
- 중복 없이, 실제로 텍스트에 근거한 키워드만 포함.
- 총 10-20개 사이로 추출.

{
  "keywords": ["키워드1", "키워드2", "키워드3"]
}
"""


def tag_product_layout(image_paths: list[str]) -> Optional[dict]:
    """
    상세 페이지 이미지들을 Gemini Vision으로 분석하여 구조 태깅.
    최대 8장까지 분석 (비용/속도 균형).
    """
    if not image_paths:
        return None

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("[Gemini] GEMINI_API_KEY 미설정 — AI 태깅 건너뜀")
        return None

    target_images = [p for p in image_paths[:8] if os.path.exists(p)]
    if not target_images:
        return None

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        pil_images = []
        for path in target_images:
            try:
                img = Image.open(path).convert("RGB")
                # 너무 큰 이미지는 리사이즈 (API 비용 절감)
                if max(img.size) > 1500:
                    img.thumbnail((1500, 1500), Image.LANCZOS)
                pil_images.append(img)
            except Exception as e:
                logger.warning(f"[Gemini] 이미지 열기 실패: {path} - {e}")

        if not pil_images:
            return None

        content = [LAYOUT_TAGGING_PROMPT] + pil_images
        response = model.generate_content(
            content,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=3000,
            ),
        )

        result_text = response.text.strip()
        # JSON 블록만 추출
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        result = json.loads(result_text)
        logger.info(f"[Gemini Layout] 섹션 {len(result.get('sections', []))}개 분류 완료")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"[Gemini Layout] JSON 파싱 실패: {e}\n응답: {response.text[:300]}")
        return None
    except Exception as e:
        logger.error(f"[Gemini Layout] Vision API 호출 실패: {e}")
        return None


def extract_keywords_from_text(
    product_name: str,
    brand: str,
    description: str,
    hashtags: list[str],
) -> list[str]:
    """
    제품 텍스트 정보에서 Gemini로 마케팅 키워드 추출.
    반환: 키워드 문자열 리스트
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return []

    # 텍스트가 너무 적으면 건너뜀
    combined_text = f"{description} {' '.join(hashtags)}"
    if len(combined_text.strip()) < 10:
        return []

    prompt = KEYWORD_EXTRACTION_PROMPT.format(
        brand=brand or "미상",
        product_name=product_name or "",
        description=(description or "")[:1000],
        hashtags=", ".join(hashtags[:20]) if hashtags else "없음",
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=500,
            ),
        )

        result_text = response.text.strip()
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        result = json.loads(result_text)
        keywords = result.get("keywords", [])
        logger.info(f"[Gemini Keywords] {len(keywords)}개 키워드 추출")
        return keywords

    except Exception as e:
        logger.error(f"[Gemini Keywords] 키워드 추출 실패: {e}")
        return []


def process_product_tagging(product_id: str, image_paths: list[str], db) -> None:
    """
    AI 레이아웃 분석 결과를 DB에 저장.
    크롤링 파이프라인에서 신규 상품 처리 후 호출.
    """
    from database import crud
    from database.models import SectionCategoryEnum

    result = tag_product_layout(image_paths)
    if not result:
        return

    # 섹션 구조 저장
    sections = result.get("sections", [])
    formatted_sections = []
    for s in sections:
        cat_str = s.get("category", "Other")
        try:
            cat_enum = SectionCategoryEnum(cat_str)
        except ValueError:
            cat_enum = SectionCategoryEnum.other

        formatted_sections.append({
            "order": s.get("order", 0),
            "category": cat_enum,
            "text": s.get("extracted_text", ""),
            "description": s.get("description", ""),
        })

    if formatted_sections:
        crud.create_layout_sections(db, product_id, formatted_sections)

    # 무드·컬러·타겟 태그 저장
    extra_tags = []
    if result.get("overall_mood"):
        extra_tags.append(f"무드:{result['overall_mood']}")
    if result.get("color_palette"):
        extra_tags.append(f"컬러:{result['color_palette']}")
    if result.get("target_audience"):
        extra_tags.append(f"타겟:{result['target_audience']}")
    if extra_tags:
        crud.create_tags(db, product_id, extra_tags)

    logger.info(f"[Gemini] 상품 {product_id} 레이아웃 + 태그 DB 저장 완료")
