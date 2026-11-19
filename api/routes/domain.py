import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import dns.asyncresolver
import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from core.cache import section_cache
from core.models import DomainLookupResponse, ProviderResult
from core.ratelimit import LocalRateLimiter
from core.validate import normalize_domain
from providers import dns as dns_provider
from providers import ip as ip_provider
from providers import rdap as rdap_provider
from providers import subdomains as subdomains_provider

router = APIRouter(prefix="/api", tags=["domain"])
_SECTION_TIMEOUTS = {"dns": 6.0, "rdap": 8.0, "subdomains": 12.0, "ip": 6.0}
_SOURCE_NAMES = {
    "dns": "system DNS resolver",
    "rdap": "IANA RDAP bootstrap",
    "subdomains": "crt.sh / Certspotter",
    "ip": "Team Cymru DNS",
}


async def _load_section(
    request: Request,
    domain: str,
    section: str,
    refresh: bool,
) -> ProviderResult:
    if not refresh:
        cached = await section_cache.get(domain, section)
        if cached is not None:
            return cached

    client: httpx.AsyncClient = request.app.state.http_client
    resolver: dns.asyncresolver.Resolver = request.app.state.dns_resolver
    providers: dict[str, Callable[[], Awaitable[tuple[str, dict[str, Any]]]]] = {
        "dns": lambda: dns_provider.lookup(domain, resolver),
        "rdap": lambda: rdap_provider.lookup(domain, client),
        "subdomains": lambda: subdomains_provider.lookup(domain, client),
        "ip": lambda: ip_provider.lookup(domain, resolver),
    }
    source = _SOURCE_NAMES[section]
    fetched_at = datetime.now(UTC)
    try:
        async with asyncio.timeout(_SECTION_TIMEOUTS[section]):
            source, data = await providers[section]()
        result = ProviderResult(
            section=section,
            status="ok",
            source=source,
            fetched_at=fetched_at,
            cached=False,
            data=data,
        )
        await section_cache.set(domain, result)
        return result
    except (TimeoutError, httpx.TimeoutException):
        return ProviderResult(
            section=section,
            status="timeout",
            source=source,
            fetched_at=fetched_at,
            message=f"{section.upper()} lookup timed out.",
        )
    except Exception:  # noqa: BLE001 - isolate failures from each independent provider
        return ProviderResult(
            section=section,
            status="error",
            source=source,
            fetched_at=fetched_at,
            message=f"{section.upper()} data source is unavailable.",
        )


def _domain_or_422(value: str) -> str:
    try:
        return normalize_domain(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="Enter a valid domain name."
        ) from exc


async def _rate_limit(request: Request, refresh: bool) -> None:
    limiter: LocalRateLimiter = request.app.state.rate_limiter
    await limiter.check(request, refresh=refresh)


async def _all_sections(
    request: Request, domain: str, refresh: bool
) -> dict[str, ProviderResult]:
    semaphore: asyncio.Semaphore = request.app.state.lookup_semaphore
    async with semaphore:
        names = ("dns", "rdap", "subdomains", "ip")
        results = await asyncio.gather(
            *(_load_section(request, domain, section, refresh) for section in names)
        )
    return {result.section: result for result in results}


@router.get("/domain/{name}", response_model=DomainLookupResponse)
async def lookup_domain(
    name: str,
    request: Request,
    refresh: bool = Query(default=False),
) -> DomainLookupResponse:
    await _rate_limit(request, refresh)
    domain = _domain_or_422(name)
    sections = await _all_sections(request, domain, refresh)
    return DomainLookupResponse(domain=domain, sections=sections)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'), ensure_ascii=True)}\n\n"


@router.get("/domain/{name}/stream")
async def stream_domain(
    name: str,
    request: Request,
    refresh: bool = Query(default=False),
) -> StreamingResponse:
    await _rate_limit(request, refresh)
    domain = _domain_or_422(name)

    async def events() -> AsyncIterator[str]:
        semaphore: asyncio.Semaphore = request.app.state.lookup_semaphore
        async with semaphore:
            names = ("dns", "rdap", "subdomains", "ip")
            tasks = [
                asyncio.create_task(_load_section(request, domain, section, refresh))
                for section in names
            ]
            try:
                for completed in asyncio.as_completed(tasks):
                    result = await completed
                    yield _sse("section", result.model_dump(mode="json"))
                yield _sse("done", {"domain": domain, "sections": len(names)})
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
