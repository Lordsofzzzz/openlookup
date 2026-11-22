import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from core.models import ProviderResult
from providers import dns, email_security, ip, rdap, subdomains
from providers.dns_resolver import DNS_SOURCE, DNSResolverPool


class LookupBusy(Exception):
    pass


@dataclass(frozen=True)
class Section:
    source: str
    timeout: float
    run: Callable[[str], Awaitable[tuple[str, dict[str, Any]]]]


class LookupService:
    def __init__(
        self, client: httpx.AsyncClient, resolver: DNSResolverPool, capacity: int
    ):
        self.slots = asyncio.Semaphore(capacity)
        self.sections = {
            "dns": Section(DNS_SOURCE, 6, lambda name: dns.lookup(name, resolver)),
            "rdap": Section(
                "IANA RDAP bootstrap", 8, lambda name: rdap.lookup(name, client)
            ),
            "subdomains": Section(
                "Cert Spotter", 12, lambda name: subdomains.lookup(name, client)
            ),
            "ip": Section(
                f"Team Cymru DNS via {DNS_SOURCE}",
                12,
                lambda name: ip.lookup(name, resolver),
            ),
            "email_security": Section(
                DNS_SOURCE, 6, lambda name: email_security.lookup(name, resolver)
            ),
        }

    async def acquire(self):
        try:
            await asyncio.wait_for(self.slots.acquire(), timeout=2)
        except TimeoutError as exc:
            raise LookupBusy from exc

    async def lookup_section(self, domain: str, key: str) -> ProviderResult:
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
            result.message = f"{key.upper()} data source is unavailable."
        return result
