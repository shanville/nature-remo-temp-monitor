"""
config.py
Runtime configuration for the Nature Remo temperature collector so other modules
can stay focused on IO logic instead of environment parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
import os

# Tunables are centralized here to avoid magic numbers scattered across files.
DEFAULT_DEVICE_ENDPOINT: Final[str] = "https://api.nature.global/1/devices"
DEFAULT_TABLE_NAME: Final[str] = "temperature_logs"
REQUEST_TIMEOUT_SECONDS: Final[int] = 10


@dataclass(frozen=True)
class EnvConfig:
    """Typed view of the required environment variables."""

    nature_remo_api_key: str
    turso_database_url: str
    turso_auth_token: str


def _require_env(key: str) -> str:
    """Pull an environment variable or raise a helpful error message."""

    value = os.getenv(key)
    if not value:
        raise ValueError(f"{key} が設定されていません")
    return value


def load_env_config() -> EnvConfig:
    """Collect all secrets up front so downstream code remains simple."""

    return EnvConfig(
        nature_remo_api_key=_require_env("NATURE_REMO_API_KEY"),
        turso_database_url=_require_env("TURSO_DATABASE_URL"),
        turso_auth_token=_require_env("TURSO_AUTH_TOKEN"),
    )

