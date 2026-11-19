import asyncio
import time

from cachetools import TTLCache

from .models import ProviderResult

_SECTION_TTLS = {
    "dns": 300,
    "ip": 300,
    "subdomains": 3600,
    "rdap": 86400,
    "email_security": 300,
}
_MAX_TTL = max(_SECTION_TTLS.values())


class SectionCache:
    """Process-local TTL cache. All access is guarded because cachetools is not thread-safe."""

    def __init__(self) -> None:
        self._cache: TTLCache[tuple[str, str], tuple[float, ProviderResult]] = TTLCache(
            maxsize=8192, ttl=_MAX_TTL
        )
        self._lock = asyncio.Lock()

    async def get(self, domain: str, section: str) -> ProviderResult | None:
        key = (domain, section)
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            expires_at, result = entry
            if time.monotonic() >= expires_at:
                self._cache.pop(key, None)
                return None
            return result.model_copy(update={"cached": True}, deep=True)

    async def set(self, domain: str, result: ProviderResult) -> None:
        ttl = _SECTION_TTLS[result.section]
        async with self._lock:
            self._cache[(domain, result.section)] = (
                time.monotonic() + ttl,
                result.model_copy(deep=True),
            )


section_cache = SectionCache()
