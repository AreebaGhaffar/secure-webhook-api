from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a .env file."""

    database_url: str = Field(min_length=1)
    webhook_secret: str = Field(min_length=1)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings() -> Settings:
    """Load settings, or stop with a clear error if configuration is missing."""
    try:
        return Settings()
    except ValidationError as exc:
        missing = sorted(
            {str(err["loc"][0]).upper() for err in exc.errors() if err["loc"]}
        )
        raise RuntimeError(
            "Missing or invalid required configuration: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and set these values."
        ) from None