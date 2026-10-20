from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration, overridable through environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "PolicySearcher"
    database_url: str = "postgresql+psycopg2://policy:policy@127.0.0.1:5432/policy_search"
    opensearch_url: str = "http://127.0.0.1:9200"
    opensearch_index: str = "policy_documents"
    opensearch_username: str | None = None
    opensearch_password: str | None = None
    cors_origins: str = "*"

    # Authentication
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    admin_username: str = "admin"
    admin_password_hash: str = ""
    api_token_expire_days: int = 90
    auth_required: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
