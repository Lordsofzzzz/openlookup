import asyncio
import ipaddress
from typing import Any

import dns.resolver

from .dns_resolver import DNS_SOURCE, DNSResolverPool


def _cymru_query(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    pointer = address.reverse_pointer
    if address.version == 4:
        return f"{pointer.removesuffix('.in-addr.arpa')}.origin.asn.cymru.com"
    return f"{pointer.removesuffix('.ip6.arpa')}.origin6.asn.cymru.com"


async def _asn_record(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    resolver: DNSResolverPool,
) -> list[dict[str, str | None]]:
    results = await resolver.resolve(_cymru_query(address), "TXT")
    records: dict[tuple[str, str], dict[str, str | None]] = {}
    for answer in results:
        if resolver.is_failure(answer) or isinstance(answer, dns.resolver.NXDOMAIN):
            continue
        if answer.rrset is None:
            continue
        for response in answer:
            parts = (
                b"".join(response.strings)
                .decode("utf-8", errors="replace")
                .split(" | ")
            )
            if len(parts) < 5:
                continue
            asn = parts[0].strip().split()[0].removeprefix("AS")
            prefix = parts[1].strip()
            key = (asn, prefix)
            records.setdefault(
                key,
                {
                    "asn": f"AS{asn}",
                    "prefix": prefix,
                    "country": parts[2].strip(),
                    "registry": parts[3].strip(),
                    "allocated": parts[4].strip(),
                    "name": None,
                },
            )

    names = await asyncio.gather(
        *(_asn_name(asn, resolver) for asn, _ in records),
    )
    for record, name in zip(records.values(), names, strict=True):
        record["name"] = name
    return list(records.values())


async def _asn_name(asn: str, resolver: DNSResolverPool) -> str | None:
    if not asn.isdigit():
        return None
    results = await resolver.resolve(f"AS{asn}.asn.cymru.com", "TXT", lifetime=3.0)
    for answer in results:
        if resolver.is_failure(answer) or isinstance(answer, dns.resolver.NXDOMAIN):
            continue
        if answer.rrset is None:
            continue
        for response in answer:
            parts = (
                b"".join(response.strings)
                .decode("utf-8", errors="replace")
                .split(" | ")
            )
            if len(parts) >= 5:
                return parts[4].strip()
    return None


async def lookup(domain: str, resolver: DNSResolverPool) -> tuple[str, dict[str, Any]]:
    resolved = await asyncio.gather(
        resolver.resolve(domain, "A"),
        resolver.resolve(domain, "AAAA"),
    )
    if all(resolver.is_failure(result) for group in resolved for result in group):
        raise TimeoutError("DNS resolver did not respond.")

    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for group in resolved:
        for answer in group:
            if resolver.is_failure(answer) or isinstance(answer, dns.resolver.NXDOMAIN):
                continue
            if answer.rrset is None:
                continue
            for record in answer:
                try:
                    address = ipaddress.ip_address(record.to_text())
                except ValueError:
                    continue
                if address.is_global:
                    addresses.add(address)

    public_addresses = sorted(
        addresses, key=lambda address: (address.version, int(address))
    )

    asn_results = await asyncio.gather(
        *(_asn_record(address, resolver) for address in public_addresses)
    )
    seen: set[tuple[str, str]] = set()
    networks: list[dict[str, str | None]] = []
    for records in asn_results:
        for record in records:
            key = (str(record["asn"]), str(record["prefix"]))
            if key not in seen:
                seen.add(key)
                networks.append(record)
    return f"Team Cymru DNS via {DNS_SOURCE}", {
        "addresses": [str(address) for address in public_addresses],
        "networks": networks,
    }
