import asyncio
from typing import Any

import dns.resolver

from core.models import ProviderOutcome

from .dns_resolver import DNS_SOURCE, DNSResolverPool

_RECORD_TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CNAME", "CAA")


def _value(record: Any, record_type: str) -> str:
    if record_type == "MX":
        return f"{record.preference} {record.exchange.to_text(omit_final_dot=True)}"
    if record_type == "NS":
        return record.target.to_text(omit_final_dot=True)
    if record_type == "CNAME":
        return record.target.to_text(omit_final_dot=True)
    if record_type == "TXT":
        return b"".join(record.strings).decode("utf-8", errors="replace")
    return record.to_text()


async def lookup(domain: str, resolver: DNSResolverPool) -> ProviderOutcome:
    async def query(
        record_type: str,
    ) -> tuple[str, list[dict[str, Any]], bool, bool]:
        results = await resolver.resolve(domain, record_type)
        records_by_value: dict[str, dict[str, Any]] = {}
        failures = 0
        answered = False
        for answer in results:
            if resolver.is_failure(answer):
                failures += 1
                continue
            answered = True
            if isinstance(answer, dns.resolver.NXDOMAIN) or answer.rrset is None:
                continue
            ttl = int(answer.rrset.ttl)
            for record in answer:
                value = _value(record, record_type)
                existing = records_by_value.get(value)
                if existing is None:
                    records_by_value[value] = {
                        "type": record_type,
                        "name": domain,
                        "value": value,
                        "ttl": ttl,
                    }
                else:
                    existing["ttl"] = min(existing["ttl"], ttl)
        return record_type, list(records_by_value.values()), answered, failures > 0

    results = await asyncio.gather(
        *(query(record_type) for record_type in _RECORD_TYPES)
    )
    records = [record for _, found, _, _ in results for record in found]
    errors = {
        record_type: "One or more DNS resolvers failed."
        for record_type, _, _, failed in results
        if failed
    }

    if not any(answered for _, _, answered, _ in results):
        raise TimeoutError("DNS resolver did not respond.")
    return ProviderOutcome(
        DNS_SOURCE, {"records": records, "errors": errors}, partial=bool(errors)
    )
