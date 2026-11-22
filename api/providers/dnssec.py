from typing import Any

import httpx

from .http import get_json

_CLOUDFLARE_DOH_URL = "https://cloudflare-dns.com/dns-query"
_DNSSEC_ERROR_CODES = (1, 2, 6, 7, 8, 9, 10, 11, 12)


def _comments(payload: dict[str, Any]) -> str:
    comments = payload.get("Comment", [])
    if not isinstance(comments, list):
        return ""
    return " ".join(str(comment) for comment in comments).lower()


async def lookup(domain: str, client: httpx.AsyncClient) -> tuple[str, dict[str, Any]]:
    payload = await get_json(
        client,
        _CLOUDFLARE_DOH_URL,
        params={"name": domain, "type": "DNSKEY", "do": "true"},
        headers={"Accept": "application/dns-json"},
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("Status"), int):
        raise TypeError("Invalid DNSSEC resolver response.")

    dnskeys = [
        answer
        for answer in payload.get("Answer", [])
        if isinstance(answer, dict) and answer.get("type") == 48
    ]
    response_code = payload["Status"]
    authenticated = payload.get("AD") is True
    comments = _comments(payload)

    if response_code == 0 and dnskeys and authenticated:
        status = "secure"
        summary = "DNSSEC signatures validated successfully."
    elif response_code == 0 and dnskeys:
        status = "unverified"
        summary = "DNSKEY records were returned, but the resolver did not confirm DNSSEC validation."
    elif response_code == 0:
        status = "unsigned"
        summary = "No DNSKEY records were found for this domain."
    elif response_code == 3:
        status = "not_found"
        summary = "The DNS lookup returned NXDOMAIN."
    elif response_code == 2 and any(
        f"ede: {code} " in comments for code in _DNSSEC_ERROR_CODES
    ):
        status = "bogus"
        summary = "The resolver reported a DNSSEC validation failure."
    else:
        status = "indeterminate"
        summary = "The resolver could not determine the DNSSEC status."

    return "Cloudflare DNSSEC validation", {
        "status": status,
        "summary": summary,
        "dnskey_count": len(dnskeys),
    }
