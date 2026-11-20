import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().with_name(".env"))


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    return tuple(
        value.strip().rstrip("/")
        for value in os.getenv(name, default).split(",")
        if value.strip()
    )


@dataclass(frozen=True)
class Settings:
    cors_origins: tuple[str, ...] = _csv_env("CORS_ORIGINS", "http://localhost:5173")
    max_concurrent_lookups: int = int(os.getenv("MAX_CONCURRENT_LOOKUPS", "12"))
    certspotter_api_key: str | None = os.getenv("CERTSPOTTER_API_KEY") or None
    max_provider_response_bytes: int = 2_000_000


settings = Settings()
