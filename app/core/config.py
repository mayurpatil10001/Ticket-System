"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "dev-secret-change-in-production-00000000000000000000000000000000"
    database_url: str = "sqlite:///./concave_tickets.db"
    app_env: str = "development"
    log_level: str = "INFO"

    # Request body size limit (bytes)
    max_body_size: int = 64 * 1024  # 64 KB

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


config = Config()
