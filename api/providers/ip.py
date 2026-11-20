import asyncio
import ipaddress
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver


def _cymru_query(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    pointer = address.reverse_pointer
    if address.version == 4:
        return f"{pointer.removesuffix('.in-addr.arpa')}.origin.asn.cymru.com"
    return f"{pointer.removesuffix('.ip6.arpa')}.origin6.asn.cymru.com"


async def _asn_record(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    resolver: dns.asyncresolver.Resolver,
) -> dict[str, str] | None:
    try:
        answers = await resolver.resolve(
            _cymru_query(address), "TXT", lifetime=4.0, search=False
        )
    except (
        dns.exception.Timeout,
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
    ):
        return None
    for answer in answers:
        parts = b"".join(answer.strings).decode("utf-8", errors="replace").split(" | ")
        if len(parts) < 5:
            continue
        asn = parts[0].strip().removeprefix("AS")
        name = await _asn_name(asn, resolver)
        return {
            "asn": f"AS{asn}",
            "prefix": parts[1].strip(),
            "country": parts[2].strip(),
            "registry": parts[3].strip(),
            "allocated": parts[4].strip(),
            "name": name,
        }
    return None


async def _asn_name(asn: str, resolver: dns.asyncresolver.Resolver) -> str | None:
    if not asn.isdigit():
        return None
    try:
        answers = await resolver.resolve(
            f"AS{asn}.asn.cymru.com", "TXT", lifetime=3.0, search=False
        )
    except (
        dns.exception.Timeout,
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
    ):
        return None
    for answer in answers:
        parts = b"".join(answer.strings).decode("utf-8", errors="replace").split(" | ")
        if len(parts) >= 5:
            return parts[4].strip()
    return None


async def lookup(
    domain: str, resolver: dns.asyncresolver.Resolver
) -> tuple[str, dict[str, Any]]:
    async def resolve_type(record_type: str) -> list[str] | Exception:
        try:
            answer = await resolver.resolve(
                domain,
                record_type,
                lifetime=4.0,
                raise_on_no_answer=False,
                search=False,
            )
            if answer.rrset is None:
                return []
            return [record.to_text() for record in answer]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return []
        except (dns.exception.Timeout, dns.resolver.NoNameservers) as exc:
            return exc

    resolved = await asyncio.gather(resolve_type("A"), resolve_type("AAAA"))
    if all(isinstance(value, Exception) for value in resolved):
        raise TimeoutError("DNS resolver did not respond.")

    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for value in resolved:
        if isinstance(value, list):
            for raw in value:
                try:
                    address = ipaddress.ip_address(raw)
                except ValueError:
                    continue
                if address.is_global:
                    addresses.add(address)

    public_addresses = sorted(addresses, key=str)[:4]
    asn_records = await asyncio.gather(
        *(_asn_record(address, resolver) for address in public_addresses)
    )
    seen: set[tuple[str, str]] = set()
    networks: list[dict[str, str]] = []
    for record in asn_records:
        if record and (key := (record["asn"], record["prefix"])) not in seen:
            seen.add(key)
            networks.append(record)
    return "Team Cymru DNS", {
        "addresses": [str(address) for address in public_addresses],
        "networks": networks,
    }
