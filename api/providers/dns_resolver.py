"""Shared fan-out resolver for public DNS lookups."""

import asyncio
from dataclasses import dataclass
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver

from core.diagnostics import event, failure

DNS_SERVERS = ("1.1.1.1", "1.0.0.1")
DNS_SOURCE = "Cloudflare DNS"


@dataclass
class _PendingQuery:
    task: asyncio.Task[list[Any]]
    waiters: int = 0


class DNSResolverPool:
    """Query each configured resolver and return every result in server order."""

    def __init__(self, max_concurrent_queries: int = 24) -> None:
        resolver = dns.asyncresolver.Resolver(configure=False)
        resolver.nameservers = list(DNS_SERVERS)
        resolver.timeout = 2.0
        resolver.lifetime = 4.0
        resolver.retry_servfail = True
        self.resolvers = [(DNS_SOURCE, resolver)]
        self._pending: dict[tuple[str, str, float], _PendingQuery] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_queries)

    @staticmethod
    def is_failure(result: Any) -> bool:
        return isinstance(result, Exception) and not isinstance(
            result, dns.resolver.NXDOMAIN
        )

    async def resolve(
        self,
        name: str,
        record_type: str,
        *,
        lifetime: float = 4.0,
    ) -> list[Any]:
        key = (name, record_type, lifetime)
        pending = self._pending.get(key)
        if pending is None or pending.task.done():
            pending = _PendingQuery(
                asyncio.create_task(self._resolve(name, record_type, lifetime))
            )
            self._pending[key] = pending
        pending.waiters += 1
        try:
            return await asyncio.shield(pending.task)
        finally:
            pending.waiters -= 1
            if not pending.waiters:
                if self._pending.get(key) is pending:
                    del self._pending[key]
                if not pending.task.done():
                    pending.task.cancel()

    async def _resolve(self, name: str, record_type: str, lifetime: float) -> list[Any]:
        async def query(
            server_name: str,
            resolver: dns.asyncresolver.Resolver,
        ) -> Any:
            async with self._semaphore:
                try:
                    return await resolver.resolve(
                        name,
                        record_type,
                        lifetime=lifetime,
                        raise_on_no_answer=False,
                        search=False,
                    )
                except dns.resolver.NXDOMAIN as exc:
                    return exc
                except (dns.exception.DNSException, OSError, TimeoutError) as exc:
                    event(
                        "dns_upstream_failed",
                        provider=server_name,
                        record_type=record_type,
                        **failure(exc),
                    )
                    return exc

        return await asyncio.gather(
            *(query(server_name, resolver) for server_name, resolver in self.resolvers)
        )
