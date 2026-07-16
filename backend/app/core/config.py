"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AutoClaim AI"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(default="dev-secret-key-change-in-production-min-32-chars!!")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    database_url: str = "postgresql+asyncpg://autoclaim:autoclaim_secret@localhost:5432/autoclaim"
    database_url_sync: str = "postgresql://autoclaim:autoclaim_secret@localhost:5432/autoclaim"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    cors_origins: str = "http://localhost:5173,http://localhost:80"
    allowed_hosts: str = "localhost,127.0.0.1,backend"

    file_storage_path: str = "/data/uploads"
    max_upload_size_mb: int = 15
    rate_limit_per_minute: int = 60
    login_rate_limit_per_minute: int = 10

    aes_master_key: str = "dev-only-change-me-32-bytes-key!!"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@autoclaim.ai"
    sms_provider: str = "console"
    sentry_dsn: str = ""
    enable_virus_scan: bool = False
    mfa_issuer: str = "AutoClaimAI"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_host_list(self) -> List[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def database_url_sync_normalized(self) -> str:
        # If DATABASE_URL is set but DATABASE_URL_SYNC is not, fallback to database_url
        raw_url = self.database_url_sync
        if not raw_url or raw_url == "postgresql://autoclaim:autoclaim_secret@localhost:5432/autoclaim":
            if self.database_url != "postgresql+asyncpg://autoclaim:autoclaim_secret@localhost:5432/autoclaim":
                raw_url = self.database_url

        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql://", 1)
        elif raw_url.startswith("postgresql+asyncpg://"):
            raw_url = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return raw_url

    @property
    def database_url_async_normalized(self) -> str:
        raw_url = self.database_url
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif raw_url.startswith("postgresql://"):
            raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return raw_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
