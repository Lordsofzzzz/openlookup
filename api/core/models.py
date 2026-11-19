from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ProviderStatus = Literal["ok", "error", "timeout"]


class ProviderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    status: ProviderStatus
    source: str
    fetched_at: datetime
    cached: bool = False
    data: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None


class DomainLookupResponse(BaseModel):
    domain: str
    sections: dict[str, ProviderResult]
