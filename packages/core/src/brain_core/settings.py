from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration currently required by the foundation services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: PostgresDsn = PostgresDsn("postgresql+psycopg://brain:brain@localhost:5432/brain")
    local_bearer_token: SecretStr | None = None
    local_organization_id: UUID = UUID("10000000-0000-0000-0000-000000000001")
    local_principal_id: UUID = UUID("20000000-0000-0000-0000-000000000001")
    local_group_ids: tuple[UUID, ...] = ()


@lru_cache
def get_settings() -> Settings:
    return Settings()
