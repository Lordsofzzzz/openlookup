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
    dns_cache_ttl_seconds: int = int(os.getenv("DNS_CACHE_TTL_SECONDS", "120"))
    dnssec_cache_ttl_seconds: int = int(os.getenv("DNSSEC_CACHE_TTL_SECONDS", "120"))
    email_security_cache_ttl_seconds: int = int(
        os.getenv("EMAIL_SECURITY_CACHE_TTL_SECONDS", "120")
    )
    rdap_cache_ttl_seconds: int = int(os.getenv("RDAP_CACHE_TTL_SECONDS", "3600"))
    ip_cache_ttl_seconds: int = int(os.getenv("IP_CACHE_TTL_SECONDS", "600"))
    subdomains_cache_ttl_seconds: int = int(
        os.getenv("SUBDOMAINS_CACHE_TTL_SECONDS", "3600")
    )
    exposure_cache_ttl_seconds: int = int(
        os.getenv("EXPOSURE_CACHE_TTL_SECONDS", "3600")
    )
    certspotter_api_key: str | None = os.getenv("CERTSPOTTER_API_KEY") or None
    max_provider_response_bytes: int = 2_000_000


settings = Settings()
