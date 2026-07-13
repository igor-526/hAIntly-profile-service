from functools import cached_property

from pydantic import AnyHttpUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    app_title: str = Field(default="FastAPI Template", alias="APP_TITLE")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    sentry_enabled: bool = Field(default=False, alias="SENTRY_ENABLED")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE", ge=0.0, le=1.0)
    sentry_release: str | None = Field(default=None, alias="SENTRY_RELEASE")

    postgres_user: str = Field(default="app", alias="POSTGRES_USER")
    postgres_password: str = Field(default="app", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="app", alias="POSTGRES_DB")

    hh_token_encrypt_key: str = Field(alias="HH_TOKEN_ENCRYPT_KEY")
    hh_redirect_url: AnyHttpUrl = Field(alias="HH_REDIRECT_URL")
    hh_client_id: str = Field(alias="HH_CLIENT_ID")
    hh_client_secret: str = Field(alias="HH_CLIENT_SECRET")
    hh_auth_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("https://hh.ru/oauth/authorize"), alias="HH_AUTH_URL"
    )
    hh_token_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("https://api.hh.ru/token"), alias="HH_TOKEN_URL"
    )
    hh_profile_url: AnyHttpUrl = Field(
        default_factory=lambda: AnyHttpUrl("https://api.hh.ru/me"), alias="HH_PROFILE_URL"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        if self.sentry_enabled and not self.sentry_dsn:
            raise ValueError("SENTRY_DSN is required when SENTRY_ENABLED=true")
        from cryptography.fernet import Fernet

        try:
            Fernet(self.hh_token_encrypt_key.encode())
        except (ValueError, TypeError) as exc:
            raise ValueError("HH_TOKEN_ENCRYPT_KEY must be a valid Fernet key") from exc
        if not self.hh_client_id or not self.hh_client_secret:
            raise ValueError("HH OAuth credentials are required")
        return self

    @cached_property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @cached_property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()  # type: ignore[call-arg]
