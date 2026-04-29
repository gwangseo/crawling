"""
CLIP 모델을 사용한 이미지 벡터화 (임베딩)
- 로컬 실행으로 OpenAI API 비용 없음
- 512차원 벡터 생성 (pgvector와 호환)
- 유사 이미지 검색의 핵심 데이터
"""
import os
import io
from typing import Optional
from loguru import logger

import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel


_model = None
_processor = None
MODEL_NAME = "openai/clip-vit-base-patch32"


def _load_model():
    global _model, _processor
    if _model is None:
        logger.info("[CLIP] 모델 로딩 중... (최초 1회만 다운로드)")
        _model = CLIPModel.from_pretrained(MODEL_NAME)
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        _model.eval()
        logger.info("[CLIP] 모델 로딩 완료")
    return _model, _processor


def get_image_embedding(image_path: str) -> Optional[list[float]]:
    """
    로컬 이미지 파일에서 512차원 벡터 추출
    반환: list[float] (512개 값)
    """
    try:
        model, processor = _load_model()
        image = Image.open(image_path).convert("RGB")

        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)
            # 정규화 (코사인 유사도 계산을 위해)
            features = features / features.norm(p=2, dim=-1, keepdim=True)

        return features[0].tolist()
    except Exception as e:
        logger.error(f"[CLIP] 임베딩 실패 - {image_path}: {e}")
        return None


def get_image_embedding_from_bytes(image_bytes: bytes) -> Optional[list[float]]:
    """
    메모리의 이미지 바이트에서 벡터 추출 (업로드 이미지 검색용)
    """
    try:
        model, processor = _load_model()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        inputs = processor(images=image, return_tensors="pt")
        with torch.no_grad():
            features = model.get_image_features(**inputs)
            features = features / features.norm(p=2, dim=-1, keepdim=True)

        return features[0].tolist()
    except Exception as e:
        logger.error(f"[CLIP] 바이트 임베딩 실패: {e}")
        return None


def process_asset_embeddings(product_id: str, assets: list[dict], db) -> None:
    """
    상품의 모든 에셋 이미지에 대해 벡터 임베딩 생성 후 DB 저장
    assets: [{"id": str, "local_path": str}]
    """
    from database import crud
    import uuid as uuid_lib

    for asset in assets:
        local_path = asset.get("local_path")
        asset_id = asset.get("id")

        if not local_path or not os.path.exists(local_path):
            continue

        # GIF/MP4는 임베딩 생략 (첫 프레임 처리 복잡도로 제외)
        ext = os.path.splitext(local_path)[1].lower()
        if ext in {".gif", ".mp4", ".mov"}:
            continue

        embedding = get_image_embedding(local_path)
        if embedding:
            crud.update_asset_embedding(db, uuid_lib.UUID(asset_id), embedding)
            logger.debug(f"[CLIP] 에셋 {asset_id} 임베딩 저장 완료")
