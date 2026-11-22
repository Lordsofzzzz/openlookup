from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response

from core.validate import normalize_domain
from services.lookup import LookupBusy, LookupService


async def domain_or_422(name: str) -> str:
    try:
        return normalize_domain(name)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid domain name.",
            headers={"Cache-Control": "no-store"},
        ) from exc


async def get_lookup_service(
    request: Request,
    response: Response,
    domain: Annotated[str, Depends(domain_or_422)],
) -> AsyncIterator[LookupService]:
    service = request.app.state.lookup
    section = request.path_params.get("section")
    if section is not None:
        response.headers["Cache-Control"] = "no-store"
        if section not in service.sections:
            raise HTTPException(
                404,
                "Unknown lookup section.",
                headers={"Cache-Control": "no-store"},
            )
    try:
        await service.acquire()
    except LookupBusy as exc:
        raise HTTPException(
            503,
            "Lookup capacity is busy.",
            headers={"Retry-After": "2", "Cache-Control": "no-store"},
        ) from exc
    try:
        yield service
    finally:
        service.slots.release()
