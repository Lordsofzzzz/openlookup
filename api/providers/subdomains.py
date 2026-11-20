from typing import Any

import httpx
from config import settings

from .http import get_json

_CRT_SH_URL = "https://crt.sh/"
_CERTSPOTTER_URL = "https://api.certspotter.com/v1/issuances"


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
    return sorted(names)[:1000]


async def _crtsh(domain: str, client: httpx.AsyncClient) -> list[str]:
    response = await get_json(
        client, _CRT_SH_URL, params={"q": f"%.{domain}", "output": "json"}
    )
    return _hostnames(response, domain)


async def _certspotter(domain: str, client: httpx.AsyncClient) -> list[str]:
    headers = (
        {"Authorization": f"Bearer {settings.certspotter_api_key}"}
        if settings.certspotter_api_key
        else None
    )
    response = await get_json(
        client,
        _CERTSPOTTER_URL,
        params={
            "domain": domain,
            "include_subdomains": "true",
            "expand": "dns_names",
            "page_size": "1000",
        },
        headers=headers,
    )
    return _hostnames(response, domain)


async def lookup(domain: str, client: httpx.AsyncClient) -> tuple[str, dict[str, Any]]:
    try:
        names = await _crtsh(domain, client)
        return "crt.sh", {"subdomains": names, "count": len(names)}
    except (httpx.HTTPError, ValueError, TypeError):
        names = await _certspotter(domain, client)
        return "Certspotter", {"subdomains": names, "count": len(names)}
