from typing import Annotated

from fastapi import APIRouter, Depends

from core.models import ProviderResult
from routes.common import domain_or_422, get_lookup_service
from services.lookup import LookupService

router = APIRouter(prefix="/api/v1/domain", tags=["domain"])


@router.get(
    "/{name}/sections/{section}",
    response_model=ProviderResult,
    responses={
        404: {"description": "Unknown section"},
        503: {"description": "Lookup capacity is busy"},
    },
)
async def lookup_section(
    section: str,
    domain: Annotated[str, Depends(domain_or_422)],
    service: Annotated[LookupService, Depends(get_lookup_service)],
) -> ProviderResult:
    return await service.lookup_section(domain, section, refresh=True)
