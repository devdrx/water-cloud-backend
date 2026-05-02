"""Station & sensor-reading endpoints.

All routes require a valid ``X-API-Key`` header (enforced at the router level).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_api_key
from app.models import SensorReading, Station
from app.schemas.readings import (
    HistoryResponse,
    LatestReadingResponse,
    SensorReadingOut,
)
from app.schemas.stations import StationListResponse, StationOut

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stations",
    tags=["stations"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=StationListResponse)
async def list_stations(db: AsyncSession = Depends(get_db)):
    """List all registered monitoring stations."""
    result = await db.execute(select(Station).order_by(Station.id))
    stations = result.scalars().all()
    return StationListResponse(
        stations=[StationOut.model_validate(s) for s in stations],
    )


@router.get("/{station_id}/latest", response_model=LatestReadingResponse)
async def get_latest_reading(
    station_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent sensor reading for a station."""
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.station_id == station_id)
        .order_by(desc(SensorReading.time))
        .limit(1)
    )
    reading = result.scalars().first()
    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No readings found for this station",
        )
    return LatestReadingResponse(
        reading=SensorReadingOut.model_validate(reading),
    )


@router.get("/{station_id}/history", response_model=HistoryResponse)
async def get_station_history(
    station_id: str,
    limit: int = Query(
        default=100, ge=1, le=1000,
        description="Maximum number of records to return (1–1000)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get historical readings for a station (capped at 1 000 rows)."""
    result = await db.execute(
        select(SensorReading)
        .where(SensorReading.station_id == station_id)
        .order_by(desc(SensorReading.time))
        .limit(limit)
    )
    readings = result.scalars().all()
    return HistoryResponse(
        station_id=station_id,
        count=len(readings),
        history=[SensorReadingOut.model_validate(r) for r in readings],
    )
