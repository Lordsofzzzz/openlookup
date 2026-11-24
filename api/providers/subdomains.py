from typing import Any

import httpx

from config import settings
from core.models import ProviderOutcome

from .http import get_json

_CERTSPOTTER_URL = "https://api.certspotter.com/v1/issuances"
_MAX_SUBDOMAINS = 1000
_MAX_PAGES = 10


def _hostnames(items: Any, domain: str) -> list[str]:
    names: set[str] = set()
    if not isinstance(items, list):
        return []
    for item in items:
        if isinstance(item, dict):
            values = item.get("name_value", item.get("dns_names", ""))
        else:
            values = item
        if isinstance(values, list):
            candidates = values
        elif isinstance(values, str):
            candidates = values.splitlines()
        else:
            continue
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            host = candidate.strip().lower().removeprefix("*.").rstrip(".")
            if host != domain and host.endswith(f".{domain}") and len(host) <= 253:
                names.add(host)
    return sorted(names)


async def _certspotter(
    domain: str, client: httpx.AsyncClient
) -> tuple[list[str], bool]:
    headers = (
        {"Authorization": f"Bearer {settings.certspotter_api_key}"}
        if settings.certspotter_api_key
        else None
    )
    params = {
        "domain": domain,
        "include_subdomains": "true",
        "expand": "dns_names",
    }
    names: set[str] = set()
    after: str | None = None

    for page_number in range(_MAX_PAGES):
        page_params = {**params}
        if after is not None:
            page_params["after"] = after
        response = await get_json(
            client, _CERTSPOTTER_URL, params=page_params, headers=headers
        )
        if not isinstance(response, list):
            raise TypeError("Invalid Cert Spotter response.")
        if not response:
            return sorted(names), False

        names.update(_hostnames(response, domain))
        if len(names) > _MAX_SUBDOMAINS:
            return sorted(names)[:_MAX_SUBDOMAINS], True

        last_issuance = response[-1]
        next_after = (
            last_issuance.get("id") if isinstance(last_issuance, dict) else None
        )
        if isinstance(next_after, int) and not isinstance(next_after, bool):
            next_after = str(next_after)
        if not isinstance(next_after, str) or not next_after or next_after == after:
            return sorted(names)[:_MAX_SUBDOMAINS], True
        after = next_after

    return sorted(names)[:_MAX_SUBDOMAINS], True


async def lookup(domain: str, client: httpx.AsyncClient) -> ProviderOutcome:
    names, truncated = await _certspotter(domain, client)
    return ProviderOutcome(
        "Cert Spotter",
        {
            "subdomains": names,
            "count": len(names),
            "truncated": truncated,
        },
    )
