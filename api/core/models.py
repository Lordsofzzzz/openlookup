from dataclasses import dataclass
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
    data: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False
    message: str | None = None


class DomainLookupResponse(BaseModel):
    domain: str
    sections: dict[str, ProviderResult]


@dataclass(frozen=True)
class ProviderOutcome:
    source: str
    data: dict[str, Any]
    partial: bool = False
