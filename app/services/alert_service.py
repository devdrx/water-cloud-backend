"""Non-blocking email alert service.

Provides both:
* ``send_email_alert``  — *async* wrapper for the FastAPI side.
* ``trigger_alert``     — *sync* fire-and-forget for the MQTT subscriber side.

The underlying SMTP call is always offloaded to a background thread so that
neither the FastAPI event loop nor the paho-mqtt callback loop is blocked.
"""

import asyncio
import logging
import smtplib
import threading
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


# ── Internal (blocking) ────────────────────────────────────────────────────

def _send_email_sync(station_id: str, water_class: str, details: str) -> None:
    """Send an SMTP email — blocking, meant to run in a thread."""
    msg = EmailMessage()
    msg.set_content(
        f"⚠️ CRITICAL ALERT\n\n"
        f"Station {station_id} reported POLLUTED water (Class {water_class}).\n\n"
        f"Details:\n{details}\n\n"
        f"— Water Quality Monitoring System"
    )
    msg["Subject"] = (
        f"🚨 Water Quality Alert — Station {station_id} (Class {water_class})"
    )
    msg["From"] = settings.SMTP_USER
    msg["To"] = settings.ALERT_EMAIL

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as srv:
            srv.send_message(msg)
        logger.info("Alert email sent for station %s", station_id)
    except Exception:
        logger.exception("Failed to send alert email for station %s", station_id)


# ── Public API ──────────────────────────────────────────────────────────────

async def send_email_alert(
    station_id: str, water_class: str, details: str
) -> None:
    """Async wrapper — offloads SMTP to a thread pool."""
    await asyncio.to_thread(_send_email_sync, station_id, water_class, details)


def trigger_alert(station_id: str, water_class: str, payload: dict) -> None:
    """Sync entry-point used by the MQTT subscriber.

    Fires the email in a daemon thread so the MQTT message-processing loop
    is never blocked, even if the SMTP server is slow or unreachable.
    """
    details = (
        f"WQI: {payload.get('wqi')}, DO: {payload.get('do')} mg/L, "
        f"BOD: {payload.get('bod')} mg/L, COD: {payload.get('cod')} mg/L"
    )
    logger.warning(
        "[ALERT] Station: %s | Class: %s | %s",
        station_id, water_class, details,
    )
    threading.Thread(
        target=_send_email_sync,
        args=(station_id, water_class, details),
        daemon=True,
    ).start()
