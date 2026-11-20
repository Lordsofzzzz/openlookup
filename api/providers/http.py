import json
from typing import Any

import httpx
from config import settings


class ProviderResponseTooLarge(Exception):
    pass


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """Read bounded JSON from a fixed provider URL, without following redirects."""
    async with client.stream(
        "GET", url, params=params, headers=headers, follow_redirects=False
    ) as response:
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        if (
            content_length
            and int(content_length) > settings.max_provider_response_bytes
        ):
            raise ProviderResponseTooLarge
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > settings.max_provider_response_bytes:
                raise ProviderResponseTooLarge
            chunks.append(chunk)
    return json.loads(b"".join(chunks))
