"""SHAP explainability endpoint.

Returns the latest SHAP feature-importance values for a given station,
allowing the dashboard or downstream tools to explain *why* the ML ensemble
produced a particular water-quality classification.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_api_key
from app.models import SensorReading

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/shap",
    tags=["explainability"],
    dependencies=[Depends(verify_api_key)],
)


class ShapResponse(BaseModel):
    """SHAP importance payload for a single reading."""

    model_config = ConfigDict(from_attributes=True)

    station_id: str
    time: datetime
    water_class: str | None = None
    shap_values: dict[str, Any] | None = None


@router.get("/{station_id}", response_model=ShapResponse)
async def get_shap_importance(
    station_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the latest SHAP feature-importance values for a station."""
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.station_id == station_id)
        .where(SensorReading.shap_values.isnot(None))
        .order_by(desc(SensorReading.time))
        .limit(1)
    )
    reading = result.scalars().first()
    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No SHAP data found for this station",
        )
    return ShapResponse(
        station_id=reading.station_id,
        time=reading.time,
        water_class=reading.water_class,
        shap_values=reading.shap_values,
    )
