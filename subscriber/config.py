"""Subscriber-specific configuration.

Mirrors the relevant subset of ``app.config.Settings`` but produces a
**synchronous** database URL (psycopg2) because paho-mqtt is a blocking
library that runs its own thread-based event loop.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class SubscriberSettings(BaseSettings):
    """Settings consumed by the MQTT subscriber process."""

    # ── Database (sync) ──────────────────────────────────────
    POSTGRES_USER: str = "wateradmin"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "waterdb"

    # ── MQTT ─────────────────────────────────────────────────
    MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 1883
    MQTT_USER: str = "wateriot"
    MQTT_PASSWORD: str = "changeme"
    MQTT_TOPIC: str = "water_quality/stations/+"

    # ── SMTP (for alerts) ────────────────────────────────────
    SMTP_HOST: str = "smtp"
    SMTP_PORT: int = 25
    SMTP_USER: str = "alerts@watermonitor.local"
    ALERT_EMAIL: str = "stakeholder@example.com"

    @property
    def sync_database_url(self) -> str:
        """SQLAlchemy sync connection string (psycopg2 driver)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = SubscriberSettings()
