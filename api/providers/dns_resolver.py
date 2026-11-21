"""Shared fan-out resolver for public DNS lookups."""

import asyncio
import logging
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver

logger = logging.getLogger(__name__)

DNS_SERVERS = ("1.1.1.1", "1.0.0.1")
DNS_SOURCE = "Cloudflare DNS"


class DNSResolverPool:
    """Query each configured resolver and return every result in server order."""

    def __init__(self, max_concurrent_queries: int = 24) -> None:
        resolver = dns.asyncresolver.Resolver(configure=False)
        resolver.nameservers = list(DNS_SERVERS)
        resolver.timeout = 2.0
        resolver.lifetime = 4.0
        resolver.retry_servfail = True
        self.resolvers = [(DNS_SOURCE, resolver)]
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
                except (dns.exception.DNSException, OSError, TimeoutError) as exc:
                    logger.warning(
                        "DNS upstream %s failed for %s query (%s)",
                        server_name,
                        record_type,
                        type(exc).__name__,
                    )
                    return exc

        return await asyncio.gather(
            *(query(server_name, resolver) for server_name, resolver in self.resolvers)
        )
