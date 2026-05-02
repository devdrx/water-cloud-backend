"""MQTT subscriber entry-point with graceful shutdown and auto-reconnect.

Usage (inside Docker)::

    python -m subscriber.main

The process will:
1. Retry the initial MQTT connection with exponential back-off.
2. Subscribe to ``water_quality/stations/+``.
3. Delegate every message to ``handler.on_message``.
4. Reconnect automatically on unexpected disconnects.
5. Shut down cleanly on ``SIGINT`` / ``SIGTERM``.
"""

import logging
import signal
import sys
import time

import paho.mqtt.client as mqtt

from subscriber.config import settings
from subscriber.handler import on_message

# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Graceful shutdown flag ─────────────────────────────────────────────────

_running = True


def _shutdown(signum, frame):  # noqa: ANN001
    global _running
    logger.info("Received signal %s — initiating graceful shutdown…", signum)
    _running = False


# ── MQTT callbacks ─────────────────────────────────────────────────────────

def _on_connect(client, userdata, flags, rc):  # noqa: ANN001
    if rc == 0:
        logger.info(
            "Connected to MQTT broker at %s:%s",
            settings.MQTT_BROKER,
            settings.MQTT_PORT,
        )
        client.subscribe(settings.MQTT_TOPIC)
        logger.info("Subscribed to topic: %s", settings.MQTT_TOPIC)
    else:
        logger.error("MQTT connection refused (rc=%s)", rc)


def _on_disconnect(client, userdata, rc):  # noqa: ANN001
    if rc != 0:
        logger.warning(
            "Unexpected MQTT disconnect (rc=%s). Paho will auto-reconnect…", rc
        )


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    client = mqtt.Client(client_id="cloud-subscriber", clean_session=True)
    client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = on_message

    # Retry initial connection with exponential back-off
    backoff = 1
    while _running:
        try:
            logger.info(
                "Connecting to MQTT broker %s:%s …",
                settings.MQTT_BROKER,
                settings.MQTT_PORT,
            )
            client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, keepalive=60)
            break
        except Exception:
            logger.warning(
                "Cannot reach MQTT broker — retrying in %d s…", backoff
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

    if not _running:
        logger.info("Shutdown requested before connection was established.")
        sys.exit(0)

    client.loop_start()
    logger.info("MQTT subscriber is running.")

    try:
        while _running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("MQTT subscriber stopped.")


if __name__ == "__main__":
    main()
