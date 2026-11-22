import asyncio
from typing import Annotated

from core.models import DomainLookupResponse
from fastapi import APIRouter, Depends
from services.lookup import LookupService

from routes.common import domain_or_422, get_lookup_service

router = APIRouter(prefix="/api/v1/domain", tags=["domain"])


@router.get("/{name}", response_model=DomainLookupResponse)
async def lookup_domain(
    domain: Annotated[str, Depends(domain_or_422)],
    service: Annotated[LookupService, Depends(get_lookup_service)],
) -> DomainLookupResponse:
    results = await asyncio.gather(
        *(service.lookup_section(domain, key) for key in service.sections)
    )
    return DomainLookupResponse(
        domain=domain, sections={result.section: result for result in results}
    )
