"""Application configuration.

Loads settings from environment variables (and a local ``.env`` file) into a
single, validated ``Settings`` object. Importing :data:`settings` is the only
sanctioned way to read configuration anywhere in the app — no module reaches for
``os.environ`` directly, so every knob is typed and discoverable in one place.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings sourced from the environment.

    Attributes:
        database_url: SQLAlchemy URL. The dialect in this URL — and nothing
            else — selects SQLite (dev) vs PostgreSQL (prod). One engine factory.
        cors_origins: Comma-separated allowlist of browser origins. Never ``*``.
        log_format: ``console`` for human-readable local logs, ``json`` for prod.
        base_currency: ISO 4217 code every salary is normalized to for comparison.
        anthropic_api_key: Key for the NL Q&A feature. Absent in tests, which use
            a mock client and never call the network.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./acme_salary.db"
    cors_origins: str = "http://localhost:5173"

    log_format: Literal["json", "console"] = "console"
    log_level: str = "INFO"

    anthropic_api_key: str | None = None
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_max_prompt_tokens: int = 4000

    base_currency: str = "USD"

    # When true, the container bootstrap seeds 10k employees on startup if the
    # database is empty. Off by default so local dev and tests never auto-seed.
    seed_on_startup: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        """Return the CORS allowlist as a clean list of origins.

        The value is stored as a comma-separated string because that is how it
        arrives from the environment; this splits and trims it. An empty setting
        yields an empty list (deny all), never a wildcard.
        """
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        """Return ``True`` when the configured database is SQLite."""
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so the ``.env`` file is parsed once. Tests override the dependency
    rather than mutating this, keeping configuration immutable at runtime.
    """
    return Settings()


settings = get_settings()
