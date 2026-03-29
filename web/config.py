"""Runtime configuration for the Tetris API."""

from __future__ import annotations

import os
from dataclasses import dataclass


_VALID_SSL_MODES = {"disable", "prefer", "require"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    db_pool_size: int = 10
    db_ssl_mode: str | None = None

    @property
    def asyncpg_ssl(self) -> bool | None:
        """Translate ssl mode to asyncpg `ssl` argument."""
        if self.db_ssl_mode == "disable":
            return False
        if self.db_ssl_mode == "require":
            return True
        # For "prefer" or if the mode is not set, asyncpg's `ssl` parameter should be `None`.
        return None


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer; got {raw!r}.") from exc

    if value <= 0:
        raise RuntimeError(f"Environment variable {name} must be greater than 0; got {value}.")

    return value


def load_settings() -> Settings:
    """Load and validate environment configuration."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Missing required environment variable DATABASE_URL. "
            "Set it to a PostgreSQL DSN before starting the API."
        )

    db_pool_size = _read_int("DB_POOL_SIZE", default=10)

    raw_ssl_mode = os.getenv("DB_SSL_MODE")
    db_ssl_mode = raw_ssl_mode.lower() if raw_ssl_mode else None

    if db_ssl_mode and db_ssl_mode not in _VALID_SSL_MODES:
        valid = ", ".join(sorted(_VALID_SSL_MODES))
        raise RuntimeError(
            f"Environment variable DB_SSL_MODE must be one of: {valid}. "
            f"Got {raw_ssl_mode!r}."
        )

    return Settings(
        database_url=database_url,
        db_pool_size=db_pool_size,
        db_ssl_mode=db_ssl_mode,
    )
