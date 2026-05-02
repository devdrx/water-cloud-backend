"""Pydantic response models for sensor-reading endpoints.

The schema is the **superset** of both research papers:
* Cloud 1: pH, DO, BOD, COD, EC, Turbidity, Temperature, Flow Rate
* Cloud 2: pH, DO, EC, Turbidity, Temperature, Ammonia (NH3), River Depth

Fields not reported by a given edge node will be ``null``.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class SensorReadingOut(BaseModel):
    """Full sensor reading record."""

    model_config = ConfigDict(from_attributes=True)

    time: datetime
    station_id: str

    # ── Core parameters (both papers) ────────────────────────────────
    ph: Decimal | None = None
    do: Decimal | None = None
    turbidity: Decimal | None = None
    ec: Decimal | None = None
    temperature: Decimal | None = None

    # ── Cloud 1 additional sensors ───────────────────────────────────
    bod: Decimal | None = None
    cod: Decimal | None = None
    flow_rate: Decimal | None = None

    # ── Cloud 2 additional sensors ───────────────────────────────────
    ammonia: Decimal | None = None          # NH3 mg/L
    river_depth: Decimal | None = None      # YOLOv8 estimate (m)

    # ── Derived / ML outputs ─────────────────────────────────────────
    wqi: Decimal | None = None
    water_class: str | None = None

    # ── Edge metadata ────────────────────────────────────────────────
    edge_latency_ms: int | None = None
    battery_voltage: Decimal | None = None
    duty_cycle_s: int | None = None
    missing_flags: dict[str, Any] | None = None
    shap_values: dict[str, Any] | None = None


class LatestReadingResponse(BaseModel):
    """Wrapper for ``GET /stations/{id}/latest``."""

    reading: SensorReadingOut


class HistoryResponse(BaseModel):
    """Wrapper for ``GET /stations/{id}/history``."""

    station_id: str
    count: int
    history: list[SensorReadingOut]
