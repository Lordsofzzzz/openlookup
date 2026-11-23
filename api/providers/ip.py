import asyncio
import ipaddress
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver

from .dns_resolver import DNSResolverPool


def _cymru_query(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    pointer = address.reverse_pointer
    if address.version == 4:
        return f"{pointer.removesuffix('.in-addr.arpa')}.origin.asn.cymru.com"
    return f"{pointer.removesuffix('.ip6.arpa')}.origin6.asn.cymru.com"


def _system_resolver() -> dns.asyncresolver.Resolver:
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = 2.0
    resolver.lifetime = 5.0
    return resolver


async def _txt_records(name: str, resolver: dns.asyncresolver.Resolver) -> list[str]:
    for attempt in range(2):
        try:
            answers = await resolver.resolve(
                name, "TXT", search=False, raise_on_no_answer=False
            )
            break
        except dns.resolver.NXDOMAIN:
            return []
        except (dns.exception.Timeout, dns.resolver.NoNameservers, OSError):
            if attempt:
                raise
    if answers.rrset is None:
        return []
    return [
        b"".join(answer.strings).decode("utf-8", errors="replace") for answer in answers
    ]


async def _asn_record(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    resolver: dns.asyncresolver.Resolver,
) -> tuple[list[dict[str, str | None]], bool]:
    records: dict[tuple[str, str], dict[str, str | None]] = {}
    try:
        answers = await _txt_records(_cymru_query(address), resolver)
    except (dns.exception.DNSException, OSError, TimeoutError):
        return [], True

    for answer in answers:
        parts = answer.split(" | ")
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
        *(_asn_name(asn, resolver) for asn, _ in records), return_exceptions=True
    )
    failed = False
    for record, name in zip(records.values(), names, strict=True):
        if isinstance(name, Exception):
            failed = True
        else:
            record["name"] = name
    return list(records.values()), failed


async def _asn_name(asn: str, resolver: dns.asyncresolver.Resolver) -> str | None:
    if not asn.isdigit():
        return None
    answers = await _txt_records(f"AS{asn}.asn.cymru.com", resolver)
    for answer in answers:
        parts = answer.split(" | ")
        if len(parts) >= 5:
            return parts[4].strip()
    return None


async def resolve_public_addresses(
    domain: str, resolver: DNSResolverPool
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Return sorted public A/AAAA addresses; raise TimeoutError if DNS is down."""
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

    return sorted(addresses, key=lambda address: (address.version, int(address)))


async def lookup(domain: str, resolver: DNSResolverPool) -> tuple[str, dict[str, Any]]:
    public_addresses = await resolve_public_addresses(domain, resolver)

    asn_resolver = _system_resolver()
    asn_results = await asyncio.gather(
        *(_asn_record(address, asn_resolver) for address in public_addresses)
    )
    seen: set[tuple[str, str]] = set()
    networks: list[dict[str, str | None]] = []
    address_asns: list[dict[str, Any]] = []
    errors = []
    for address, (records, failed) in zip(public_addresses, asn_results, strict=True):
        if failed and not errors:
            errors.append("Some ASN lookups failed.")
        asns: dict[str, dict[str, str | None]] = {}
        for record in records:
            asn = str(record["asn"])
            existing_asn = asns.get(asn)
            if existing_asn is None or (
                existing_asn["name"] is None and record["name"] is not None
            ):
                asns[asn] = {"asn": asn, "name": record["name"]}
            key = (str(record["asn"]), str(record["prefix"]))
            if key not in seen:
                seen.add(key)
                networks.append(record)
        address_asns.append({"ip": str(address), "asns": list(asns.values())})

    data = {
        "addresses": [str(address) for address in public_addresses],
        "address_asns": address_asns,
        "networks": networks,
    }
    if errors:
        data["errors"] = errors
    return "Team Cymru DNS via system resolver", data
