import asyncio
import time
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from .http import get_json

_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
_bootstrap: dict[str, Any] | None = None
_bootstrap_expires = 0.0
_bootstrap_lock = asyncio.Lock()


async def _get_bootstrap(client: httpx.AsyncClient) -> dict[str, Any]:
    global _bootstrap, _bootstrap_expires
    async with _bootstrap_lock:
        if _bootstrap is not None and time.monotonic() < _bootstrap_expires:
            return _bootstrap
        payload = await get_json(client, _BOOTSTRAP_URL)
        if not isinstance(payload, dict) or not isinstance(
            payload.get("services"), list
        ):
            raise TypeError("Invalid RDAP bootstrap response.")
        _bootstrap = payload
        _bootstrap_expires = time.monotonic() + 86400
        return payload


def _registry_urls(bootstrap: dict[str, Any], tld: str) -> list[str]:
    for entry in bootstrap["services"]:
        if isinstance(entry, list) and len(entry) == 2:
            tlds, urls = entry
            if tld in tlds and isinstance(urls, list):
                return [url for url in urls if isinstance(url, str)]
    return []


def _safe_registry_url(value: str) -> str | None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        return None
    if parsed.port not in (None, 443):
        return None
    return value.rstrip("/") + "/"


def _event_date(events: list[dict[str, Any]], action: str) -> str | None:
    for event in events:
        if event.get("eventAction", "").lower() == action and isinstance(
            event.get("eventDate"), str
        ):
            return event["eventDate"]
    return None


def _entity_name(entity: dict[str, Any]) -> str | None:
    vcard = entity.get("vcardArray")
    if isinstance(vcard, list) and len(vcard) == 2 and isinstance(vcard[1], list):
        for field in vcard[1]:
            if (
                isinstance(field, list)
                and len(field) >= 4
                and field[0] in {"fn", "org"}
            ):
                value = field[3]
                if isinstance(value, str):
                    return value
                if isinstance(value, list):
                    return " ".join(str(part) for part in value)
    return None


def _registrar(entities: list[dict[str, Any]]) -> str | None:
    for entity in entities:
        if "registrar" in entity.get("roles", []):
            name = _entity_name(entity)
            if name:
                return name
        nested = entity.get("entities", [])
        if isinstance(nested, list):
            name = _registrar(nested)
            if name:
                return name
    return None


async def lookup(domain: str, client: httpx.AsyncClient) -> tuple[str, dict[str, Any]]:
    bootstrap = await _get_bootstrap(client)
    tld = domain.rsplit(".", 1)[-1]
    urls = _registry_urls(bootstrap, tld)
    registry = next((safe for url in urls if (safe := _safe_registry_url(url))), None)
    if not registry:
        raise ValueError("No RDAP registry is listed for this domain suffix.")

    endpoint = f"{registry}domain/{quote(domain, safe='.-')}"
    data = await get_json(
        client, endpoint, headers={"Accept": "application/rdap+json, application/json"}
    )
    if not isinstance(data, dict):
        raise TypeError("Invalid RDAP response.")
    entities = data.get("entities", [])
    events = data.get("events", [])
    return urlparse(registry).hostname or "RDAP registry", {
        "registrar": _registrar(entities) if isinstance(entities, list) else None,
        "created": _event_date(events, "registration")
        if isinstance(events, list)
        else None,
        "updated": _event_date(events, "last changed")
        if isinstance(events, list)
        else None,
        "expires": _event_date(events, "expiration")
        if isinstance(events, list)
        else None,
        "status": data.get("status", []),
        "nameservers": [
            server["ldhName"].lower().rstrip(".")
            for server in data.get("nameservers", [])
            if isinstance(server, dict) and isinstance(server.get("ldhName"), str)
        ],
    }
