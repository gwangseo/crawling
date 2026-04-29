from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid as uuid_lib

from database.session import get_db
from database.models import Asset, AssetTypeEnum

router = APIRouter(prefix="/api/v1/assets", tags=["Assets"])


@router.get("/{product_id}")
def get_product_assets(
    product_id: str,
    asset_type: Optional[str] = Query(None, description="에셋 타입: thumbnail, detail_image, gif, video"),
    db: Session = Depends(get_db),
):
    query = db.query(Asset).filter(Asset.product_id == uuid_lib.UUID(product_id))
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)

    assets = query.order_by(Asset.created_at).all()
    return [
        {
            "id": str(a.id),
            "asset_type": a.asset_type.value if a.asset_type else None,
            "drive_url": a.drive_url,
            "original_filename": a.original_filename,
        }
        for a in assets
        if a.drive_url
    ]
