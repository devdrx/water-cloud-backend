"""MQTT message handler with Pydantic validation, tenacity retry, and
non-blocking alerting.

Design decisions
~~~~~~~~~~~~~~~~
* **Pydantic validation** catches malformed payloads *before* a DB round-trip.
* **tenacity retry** with exponential back-off keeps the subscriber alive
  during transient DB outages (e.g. TimescaleDB restart).
* **Threaded alerts** ensure a slow/dead SMTP server never stalls the MQTT
  callback loop.
"""

import json
import logging
import smtplib
import threading
from email.message import EmailMessage
from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy import create_engine, text
from tenacity import (
    before_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from subscriber.config import settings

logger = logging.getLogger(__name__)

# ── Sync SQLAlchemy engine ─────────────────────────────────────────────────

engine = create_engine(
    settings.sync_database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

# ── Payload validation ─────────────────────────────────────────────────────


class SensorPayload(BaseModel):
    """Schema that incoming MQTT JSON payloads are validated against.

    Accepts the superset of Cloud 1 and Cloud 2 edge payloads.
    Fields not sent by a given edge node default to ``None``.
    """

    station_id: str

    # Core parameters (both papers)
    ph: float | None = None
    do: float | None = None
    turbidity: float | None = None
    ec: float | None = None
    temperature: float | None = None

    # Cloud 1 additional
    bod: float | None = None
    cod: float | None = None
    flow_rate: float | None = None

    # Cloud 2 additional
    ammonia: float | None = None         # NH3 mg/L
    river_depth: float | None = None     # YOLOv8 estimate (m)

    # Derived / ML outputs
    wqi: float | None = None
    water_class: str | None = None

    # Edge metadata
    edge_latency_ms: int | None = None
    battery_voltage: float | None = None
    duty_cycle_s: int | None = None
    missing_flags: dict[str, Any] = {}
    shap_values: dict[str, Any] = {}

    @field_validator("water_class")
    @classmethod
    def validate_water_class(cls, v: str | None) -> str | None:
        if v is not None and v not in ("A", "B", "C", "D", "E"):
            raise ValueError(f"water_class must be A–E, got '{v}'")
        return v


# ── DB insert with tenacity retry ──────────────────────────────────────────

_INSERT_QUERY = text("""
    INSERT INTO sensor_readings
        (time, station_id,
         ph, "do", turbidity, ec, temperature,
         bod, cod, flow_rate,
         ammonia, river_depth,
         wqi, water_class,
         edge_latency_ms, battery_voltage, duty_cycle_s,
         missing_flags, shap_values)
    VALUES
        (NOW(), :station_id,
         :ph, :do, :turbidity, :ec, :temperature,
         :bod, :cod, :flow_rate,
         :ammonia, :river_depth,
         :wqi, :water_class,
         :edge_latency_ms, :battery_voltage, :duty_cycle_s,
         :missing_flags, :shap_values)
""")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    before=before_log(logger, logging.WARNING),
    reraise=True,
)
def _insert_reading(payload: SensorPayload) -> None:
    """Insert a validated sensor reading with exponential-backoff retry."""
    with engine.begin() as conn:
        conn.execute(
            _INSERT_QUERY,
            {
                "station_id": payload.station_id,
                "ph": payload.ph,
                "do": payload.do,
                "turbidity": payload.turbidity,
                "ec": payload.ec,
                "temperature": payload.temperature,
                "bod": payload.bod,
                "cod": payload.cod,
                "flow_rate": payload.flow_rate,
                "ammonia": payload.ammonia,
                "river_depth": payload.river_depth,
                "wqi": payload.wqi,
                "water_class": payload.water_class,
                "edge_latency_ms": payload.edge_latency_ms,
                "battery_voltage": payload.battery_voltage,
                "duty_cycle_s": payload.duty_cycle_s,
                "missing_flags": json.dumps(payload.missing_flags),
                "shap_values": json.dumps(payload.shap_values),
            },
        )


# ── Non-blocking alert ─────────────────────────────────────────────────────

def _send_alert_email(station_id: str, water_class: str, details: str) -> None:
    """Send an SMTP alert (runs in a daemon thread)."""
    msg = EmailMessage()
    msg.set_content(
        f"⚠️ CRITICAL ALERT\n\n"
        f"Station {station_id} reported POLLUTED water (Class {water_class}).\n\n"
        f"Details:\n{details}\n\n"
        f"— Water Quality Monitoring System"
    )
    msg["Subject"] = f"🚨 Water Quality Alert — Station {station_id}"
    msg["From"] = settings.SMTP_USER
    msg["To"] = settings.ALERT_EMAIL

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as srv:
            srv.send_message(msg)
        logger.info("Alert email sent for station %s", station_id)
    except Exception:
        logger.exception("Failed to send alert email for station %s", station_id)


def _trigger_alert(station_id: str, water_class: str, payload: SensorPayload) -> None:
    """Fire the alert in a daemon thread."""
    details = (
        f"WQI: {payload.wqi}, DO: {payload.do} mg/L, "
        f"BOD: {payload.bod} mg/L, COD: {payload.cod} mg/L"
        + (f", NH3: {payload.ammonia} mg/L" if payload.ammonia is not None else "")
        + (f", Depth: {payload.river_depth} m" if payload.river_depth is not None else "")
    )
    logger.warning(
        "[ALERT] Station: %s | Class: %s | %s", station_id, water_class, details
    )
    threading.Thread(
        target=_send_alert_email,
        args=(station_id, water_class, details),
        daemon=True,
    ).start()


# ── MQTT callback ──────────────────────────────────────────────────────────

def on_message(client, userdata, msg) -> None:  # noqa: ANN001
    """Process an incoming MQTT message — validate → insert → alert."""
    try:
        raw = json.loads(msg.payload.decode())
        payload = SensorPayload(**raw)
    except Exception:
        logger.exception("Invalid payload on topic %s", msg.topic)
        return

    try:
        _insert_reading(payload)
        logger.info(
            "Inserted: %s | Class %s | WQI %s",
            payload.station_id,
            payload.water_class,
            payload.wqi,
        )
    except Exception:
        logger.exception(
            "Failed to insert reading for %s after retries",
            payload.station_id,
        )
        return

    if payload.water_class in ("D", "E"):
        _trigger_alert(payload.station_id, payload.water_class, payload)
