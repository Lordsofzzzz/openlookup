import asyncio
import re
from typing import Any

import httpx

from .dns_resolver import DNSResolverPool
from .http import ProviderResponseTooLarge, get_json
from .ip import resolve_public_addresses

_INTERNETDB_URL = "https://internetdb.shodan.io/"
_SOURCE = "Shodan InternetDB"
_MAX_HOSTS = 10
_MAX_ITEMS = 50
_CVE = re.compile(r"^CVE-\d{4}-\d{4,}$")
_TAG = re.compile(r"^[a-z0-9][a-z0-9 _.-]{0,40}$")


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item][:_MAX_ITEMS]


def _ports(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    ports = {
        item
        for item in value
        if isinstance(item, int) and not isinstance(item, bool) and 0 < item < 65536
    }
    return sorted(ports)[:_MAX_ITEMS]


def _host(address: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("Invalid InternetDB response.")
    vulns = sorted({v for v in _strings(payload.get("vulns")) if _CVE.fullmatch(v)})
    return {
        "ip": address,
        "found": True,
        "ports": _ports(payload.get("ports")),
        "cpes": _strings(payload.get("cpes")),
        "hostnames": _strings(payload.get("hostnames")),
        "tags": [t for t in _strings(payload.get("tags")) if _TAG.fullmatch(t)],
        "vulns": vulns,
    }


def _empty(address: str) -> dict[str, Any]:
    return {
        "ip": address,
        "found": False,
        "ports": [],
        "cpes": [],
        "hostnames": [],
        "tags": [],
        "vulns": [],
    }


async def _one(address: str, client: httpx.AsyncClient) -> tuple[dict[str, Any], bool]:
    """Return (host, failed). A 404 means InternetDB has no data for the IP."""
    try:
        payload = await get_json(client, f"{_INTERNETDB_URL}{address}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return _empty(address), False
        return _empty(address), True
    except (httpx.TransportError, ProviderResponseTooLarge, ValueError):
        return _empty(address), True
    try:
        return _host(address, payload), False
    except TypeError:
        return _empty(address), True


async def lookup(
    domain: str, resolver: DNSResolverPool, client: httpx.AsyncClient
) -> tuple[str, dict[str, Any]]:
    addresses = await resolve_public_addresses(domain, resolver)
    truncated = len(addresses) > _MAX_HOSTS
    selected = [str(address) for address in addresses[:_MAX_HOSTS]]
    results = await asyncio.gather(*(_one(address, client) for address in selected))

    hosts = [host for host, _ in results]
    errors = [
        f"InternetDB lookup failed for {host['ip']}."
        for host, failed in results
        if failed
    ]
    if selected and len(errors) == len(selected):
        raise httpx.TransportError("InternetDB unavailable.")
    return _SOURCE, {"hosts": hosts, "truncated": truncated, "errors": errors}
