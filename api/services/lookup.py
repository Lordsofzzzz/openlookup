import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from config import settings
from core.models import ProviderResult
from providers import dns, dnssec, email_security, ip, rdap, subdomains
from providers.dns_resolver import DNS_SOURCE, DNSResolverPool


class LookupBusy(Exception):
    pass


@dataclass(frozen=True)
class Section:
    source: str
    timeout: float
    run: Callable[[str], Awaitable[tuple[str, dict[str, Any]]]]
    cache_ttl: int


class LookupService:
    _MAX_CACHE_ENTRIES = 2048

    def __init__(
        self, client: httpx.AsyncClient, resolver: DNSResolverPool, capacity: int
    ):
        self.slots = asyncio.Semaphore(capacity)
        self._cache: OrderedDict[tuple[str, str], tuple[float, ProviderResult]] = (
            OrderedDict()
        )
        self._in_flight: dict[tuple[str, str], asyncio.Task[ProviderResult]] = {}
        self._flight_lock = asyncio.Lock()
        self.sections = {
            "dns": Section(
                DNS_SOURCE,
                6,
                lambda name: dns.lookup(name, resolver),
                max(0, settings.dns_cache_ttl_seconds),
            ),
            "dnssec": Section(
                "Cloudflare DNSSEC validation",
                6,
                lambda name: dnssec.lookup(name, client),
                max(0, settings.dnssec_cache_ttl_seconds),
            ),
            "rdap": Section(
                "IANA RDAP bootstrap",
                8,
                lambda name: rdap.lookup(name, client),
                max(0, settings.rdap_cache_ttl_seconds),
            ),
            "subdomains": Section(
                "Cert Spotter",
                12,
                lambda name: subdomains.lookup(name, client),
                max(0, settings.subdomains_cache_ttl_seconds),
            ),
            "ip": Section(
                f"Team Cymru DNS via {DNS_SOURCE}",
                12,
                lambda name: ip.lookup(name, resolver),
                max(0, settings.ip_cache_ttl_seconds),
            ),
            "email_security": Section(
                DNS_SOURCE,
                6,
                lambda name: email_security.lookup(name, resolver),
                max(0, settings.email_security_cache_ttl_seconds),
            ),
        }

    async def acquire(self):
        try:
            await asyncio.wait_for(self.slots.acquire(), timeout=2)
        except TimeoutError as exc:
            raise LookupBusy from exc

    async def lookup_section(
        self, domain: str, key: str, *, refresh: bool = False
    ) -> ProviderResult:
        cache_key = (domain, key)
        async with self._flight_lock:
            task = self._in_flight.get(cache_key)
            if task is None and not refresh:
                cached = self._cache.get(cache_key)
                if cached is not None:
                    expires_at, result = cached
                    if time.monotonic() < expires_at:
                        self._cache.move_to_end(cache_key)
                        return result.model_copy(deep=True)
                    self._cache.pop(cache_key, None)

            if task is None:
                task = asyncio.create_task(self._fetch_section(domain, key))
                self._in_flight[cache_key] = task
                task.add_done_callback(
                    lambda completed, key=cache_key: self._forget_flight(key, completed)
                )

        return (await asyncio.shield(task)).model_copy(deep=True)

    def _forget_flight(
        self, cache_key: tuple[str, str], task: asyncio.Task[ProviderResult]
    ) -> None:
        if self._in_flight.get(cache_key) is task:
            self._in_flight.pop(cache_key, None)

    async def _fetch_section(self, domain: str, key: str) -> ProviderResult:
        section = self.sections[key]
        result = ProviderResult(
            section=key,
            source=section.source,
            status="ok",
            fetched_at=datetime.now(UTC),
        )
        try:
            async with asyncio.timeout(section.timeout):
                result.source, result.data = await section.run(domain)
            if result.data.get("errors"):
                result.retryable = True
                result.message = "Some lookup data was unavailable."
        except (TimeoutError, httpx.TimeoutException):
            result.status = "timeout"
            result.retryable = True
            result.message = f"{key.upper()} lookup timed out."
        except rdap.UnsupportedSuffix as exc:
            result.status = "error"
            result.message = str(exc)
        except Exception as exc:  # noqa: BLE001 - isolate failures to this section
            result.status = "error"
            result.retryable = isinstance(exc, httpx.TransportError) or (
                isinstance(exc, httpx.HTTPStatusError)
                and (
                    exc.response.status_code in (408, 429)
                    or exc.response.status_code >= 500
                )
            )
            if (
                key == "dnssec"
                and isinstance(exc, httpx.ConnectError)
                and "CERTIFICATE_VERIFY_FAILED" in str(exc).upper()
            ):
                result.message = (
                    "DNSSEC lookup could not verify Google's TLS certificate. "
                    "Check this server's trusted certificates and HTTPS network settings."
                )
            elif (
                isinstance(exc, httpx.HTTPStatusError)
                and exc.response.status_code == 429
            ):
                result.message = (
                    f"{key.upper()} provider rate limit reached. Try again later."
                )
            else:
                result.message = f"{key.upper()} data source is unavailable."
        cache_ttl = section.cache_ttl
        if result.status == "ok" and cache_ttl:
            async with self._flight_lock:
                self._cache[(domain, key)] = (
                    time.monotonic() + cache_ttl,
                    result.model_copy(deep=True),
                )
                self._cache.move_to_end((domain, key))
                while len(self._cache) > self._MAX_CACHE_ENTRIES:
                    self._cache.popitem(last=False)
        return result
