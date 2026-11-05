"""Schemas de municípios."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import DataStatus
from .coverage import CoverageHistoryPoint


class MunicipalityItem(BaseModel):
    municipality_code: str
    municipality_name: str | None = None
    mean_coverage: float | None
    mean_deficit: float | None
    deficit_class: str | None = Field(
        default=None, description="Classe calculada sobre o déficit médio."
    )
    records: int


class MunicipalityListResponse(BaseModel):
    status: DataStatus
    message: str | None = None
    total: int = 0
    limit: int
    offset: int
    items: list[MunicipalityItem] = Field(default_factory=list)


class ImmunizerSummary(BaseModel):
    immunizer: str
    mean_coverage: float | None
    mean_deficit: float | None


class MunicipalityDetailResponse(BaseModel):
    municipality: MunicipalityItem
    history: list[CoverageHistoryPoint]
    by_immunizer: list[ImmunizerSummary] = Field(default_factory=list)
