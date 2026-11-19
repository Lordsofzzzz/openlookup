import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from config import settings


class LocalRateLimiter:
    """Per-process IP rate limiter; use a shared store if deploying multiple workers."""

    def __init__(self) -> None:
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, request: Request, refresh: bool = False) -> None:
        client_ip = request.client.host if request.client else "unknown"
        kind = "refresh" if refresh else "lookup"
        limit = (
            settings.refresh_requests_per_minute
            if refresh
            else settings.per_ip_requests_per_minute
        )
        now = time.monotonic()
        key = (client_ip, kind)
        async with self._lock:
            requests = self._requests[key]
            while requests and now - requests[0] >= 60:
                requests.popleft()
            if len(requests) >= limit:
                retry_after = max(1, int(60 - (now - requests[0])))
                raise HTTPException(
                    status_code=429,
                    detail="Too many lookups. Please try again shortly.",
                    headers={"Retry-After": str(retry_after)},
                )
            requests.append(now)
            if len(self._requests) > 10_000:
                self._requests = defaultdict(
                    deque,
                    {
                        entry: stamps
                        for entry, stamps in self._requests.items()
                        if stamps and now - stamps[-1] < 60
                    },
                )
