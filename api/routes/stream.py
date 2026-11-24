import json
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from routes.common import domain_or_422, get_lookup_service
from services.lookup import LookupService

router = APIRouter(prefix="/api/v1/domain", tags=["domain"])


def _sse(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=True)
    return f"event: {event}\ndata: {payload}\n\n"


@router.get("/{name}/stream")
async def stream_domain(
    domain: Annotated[str, Depends(domain_or_422)],
    service: Annotated[LookupService, Depends(get_lookup_service)],
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        count = 0
        async with aclosing(
            service.iter_sections(domain, completion_order=True)
        ) as results:
            async for result in results:
                count += 1
                yield _sse("section", result.model_dump(mode="json"))
        yield _sse("done", {"domain": domain, "sections": count})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform, no-store",
            "X-Accel-Buffering": "no",
        },
    )
