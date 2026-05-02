"""Pydantic response models for alert endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    """Single alert record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    time: datetime | None = None
    station_id: str
    water_class: str | None = None
    alert_type: str | None = None
    recipient: str | None = None
    message: str | None = None
    resolved: bool = False


class AlertListResponse(BaseModel):
    """Wrapper for alert list endpoints."""

    alerts: list[AlertOut]
