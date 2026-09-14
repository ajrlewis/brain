from functools import lru_cache

from pydantic import Field, HttpUrl, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    brain_url: HttpUrl | None = None
    brain_api_key: SecretStr | None = None
    brain_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    brain_read_timeout_seconds: float = Field(default=5.0, gt=0, le=60)

    @model_validator(mode="after")
    def require_complete_brain_configuration(self) -> "Settings":
        if (self.brain_url is None) != (self.brain_api_key is None):
            raise ValueError("BRAIN_URL and BRAIN_API_KEY must be configured together")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
