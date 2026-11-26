import re

import httpx

from .http import get_json

SOURCE = "WebTrustScore"
LOOKUP_URL = "https://webtrustscore.com/api/lookup"


REQUEST_TIMEOUT = httpx.Timeout(30, connect=5)


async def lookup(domain: str, client: httpx.AsyncClient):
    payload = await get_json(
        client, LOOKUP_URL, params={"domain": domain}, timeout=REQUEST_TIMEOUT
    )
    if payload.get("scored") is False:
        return SOURCE, {"scored": False}
    scan_id = payload.get("scanId")
    report = str(httpx.URL(LOOKUP_URL, params={"domain": domain}))
    if isinstance(scan_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", scan_id):
        report = f"https://webtrustscore.com/api/scan/{scan_id}"

    score = payload["score"]
    if type(score) is not int or not 0 <= score <= 1000:
        raise ValueError("Invalid WebTrustScore score")
    return SOURCE, {
        "score": score,
        "band": payload.get("band"),
        "modelVersion": payload.get("modelVersion"),
        "scannedAt": payload.get("scannedAt"),
        "report": report,
        "scored": True,
        "signals": [
            {key: signal.get(key) for key in ("label", "value", "confidence")}
            for signal in (payload.get("signals") or [])
            if isinstance(signal, dict) and isinstance(signal.get("label"), str)
        ],
    }
