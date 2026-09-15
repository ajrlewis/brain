from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, SecretStr, StringConstraints, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    brain_url: HttpUrl | None = None
    brain_api_key: SecretStr | None = None
    brain_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    brain_read_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    model_backend: Literal["deterministic", "openai"] = "deterministic"
    openai_api_key: SecretStr | None = None
    openai_model: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = (
        None
    )
    openai_timeout_seconds: float = Field(default=30.0, ge=0.1, le=120)
    openai_base_url: HttpUrl | None = None
    openai_organization: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = None
    openai_project: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = None

    @model_validator(mode="after")
    def require_complete_brain_configuration(self) -> "Settings":
        if (self.brain_url is None) != (self.brain_api_key is None):
            raise ValueError("BRAIN_URL and BRAIN_API_KEY must be configured together")
        if self.model_backend == "openai":
            if self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip():
                raise ValueError("OPENAI_API_KEY is required for the OpenAI backend")
            if self.openai_model is None:
                raise ValueError("OPENAI_MODEL is required for the OpenAI backend")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
