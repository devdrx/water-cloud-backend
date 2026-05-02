"""Pydantic response models for station endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StationOut(BaseModel):
    """Single station record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    status: str = "active"
    created_at: datetime | None = None


class StationListResponse(BaseModel):
    """Wrapper for ``GET /stations``."""

    stations: list[StationOut]
