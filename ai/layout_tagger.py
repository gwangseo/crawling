"""
Gemini Vision을 사용한 상세 페이지 구조 태깅
이미지를 분석하여 섹션 종류(Hook/Problem/Solution 등)와 텍스트를 추출
"""
import os
import json
from pathlib import Path
from typing import Optional
from loguru import logger

import google.generativeai as genai
from PIL import Image

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

TAGGING_PROMPT = """
당신은 K-뷰티 마케팅 전문 분석가입니다. 
아래 뷰티 제품 상세 페이지 이미지를 분석하여, 각 섹션을 JSON 형식으로 분류해 주세요.

분류 기준:
- Hook: 브랜드/제품명 소개, 시선을 사로잡는 핵심 카피, 감성적 이미지
- Problem: 피부 고민 언급, 문제 제기 (예: 건조함, 잡티, 트러블)
- Solution: 제품의 해결책 제시, 성분/기술 강조
- Proof: 임상 실험 결과, 실제 사용 전후 비교, 전문가/소비자 추천
- How-to: 사용 방법, 사용 순서
- Ingredient: 성분 상세 설명, 원료 소개
- Other: 위 분류에 해당하지 않는 기타 섹션

반드시 아래 JSON 형식으로만 답변하세요. JSON 외 다른 텍스트는 포함하지 마세요:
{
  "sections": [
    {
      "order": 1,
      "category": "Hook",
      "extracted_text": "이미지에서 읽히는 텍스트 (없으면 빈 문자열)",
      "description": "이 섹션이 전달하는 마케팅 메시지 1-2줄 요약"
    }
  ],
  "overall_mood": "이 상세 페이지의 전체적인 시각적 무드 (예: 미니멀, 화려함, 자연친화적, 럭셔리 등)",
  "color_palette": "주요 색상 3가지 (예: 베이지, 올리브그린, 골드)"
}
"""


def tag_product_layout(image_paths: list[str]) -> Optional[dict]:
    """
    상세 페이지 이미지들을 Gemini Vision에 전송하여 구조 태깅
    최대 5장의 이미지를 한 번에 분석

    반환:
    {
        "sections": [...],
        "overall_mood": str,
        "color_palette": str
    }
    """
    if not image_paths:
        return None

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("[Gemini] GEMINI_API_KEY가 설정되지 않아 AI 태깅을 건너뜁니다.")
        return None

    # 최대 5장만 분석 (속도 및 비용 절감)
    target_images = [p for p in image_paths[:5] if os.path.exists(p)]
    if not target_images:
        return None

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        # 이미지 열기
        pil_images = []
        for path in target_images:
            try:
                img = Image.open(path).convert("RGB")
                pil_images.append(img)
            except Exception as e:
                logger.warning(f"[Gemini] 이미지 열기 실패: {path} - {e}")

        if not pil_images:
            return None

        # Gemini에 텍스트 + 이미지 함께 전송
        content = [TAGGING_PROMPT] + pil_images

        response = model.generate_content(
            content,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=2000,
            ),
        )

        result_text = response.text.strip()

        # JSON만 추출 (앞뒤 마크다운 코드블록 제거)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        result = json.loads(result_text)
        logger.info(f"[Gemini] 섹션 {len(result.get('sections', []))}개 분류 완료")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"[Gemini] JSON 파싱 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"[Gemini] Vision API 호출 실패: {e}")
        return None


def process_product_tagging(product_id: str, image_paths: list[str], db) -> None:
    """
    크롤링 후 AI 태깅 파이프라인 실행 - DB에 결과 저장
    """
    from database import crud
    from database.models import SectionCategoryEnum

    result = tag_product_layout(image_paths)
    if not result:
        return

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

    crud.create_layout_sections(db, product_id, formatted_sections)

    # 전체 무드와 컬러 태그로도 저장
    mood = result.get("overall_mood", "")
    palette = result.get("color_palette", "")
    if mood:
        crud.create_tags(db, product_id, [f"무드:{mood}"])
    if palette:
        crud.create_tags(db, product_id, [f"컬러:{palette}"])

    logger.info(f"[Gemini] 상품 {product_id} 레이아웃 DB 저장 완료")
