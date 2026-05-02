"""Centralised configuration via pydantic-settings.

All secrets are loaded from environment variables (or a .env file in local
development).  Missing required values will cause a fast, descriptive
startup failure rather than a silent wrong-default at runtime.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings."""

    # ── Database ─────────────────────────────────────────────
    POSTGRES_USER: str = "wateradmin"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "waterdb"

    # ── API ──────────────────────────────────────────────────
    API_KEY: str = "changeme_api_key"

    # ── SMTP Alerts ──────────────────────────────────────────
    SMTP_HOST: str = "smtp"
    SMTP_PORT: int = 25
    SMTP_USER: str = "alerts@watermonitor.local"
    ALERT_EMAIL: str = "stakeholder@example.com"

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy async connection string (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
