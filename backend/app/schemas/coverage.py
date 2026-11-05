"""Schemas de cobertura vacinal e série histórica."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import DataStatus


class CoverageSummary(BaseModel):
    records: int = Field(description="Linhas (município x imunizante x ano) consideradas.")
    municipalities: int = Field(description="Municípios distintos analisados.")
    mean_coverage: float | None = Field(description="Cobertura média (%) das linhas filtradas.")
    mean_deficit: float | None = Field(description="Déficit médio (p.p.) das linhas filtradas.")
    municipalities_below_target: int = Field(description="Municípios com déficit > 0.")
    critical_municipalities: int = Field(description="Municípios com classe de déficit 'alto'.")


class DeficitDistributionItem(BaseModel):
    deficit_class: str
    count: int


class MunicipalityRankingItem(BaseModel):
    municipality_code: str
    municipality_name: str | None = None
    mean_coverage: float | None
    mean_deficit: float | None


class CoverageResponse(BaseModel):
    status: DataStatus
    message: str | None = Field(default=None, description="Motivo quando não há dados.")
    summary: CoverageSummary | None = None
    deficit_distribution: list[DeficitDistributionItem] = Field(default_factory=list)
    top_deficit_municipalities: list[MunicipalityRankingItem] = Field(default_factory=list)


class CoverageFilterOptions(BaseModel):
    status: DataStatus
    message: str | None = None
    years: list[int] = Field(default_factory=list)
    immunizers: list[str] = Field(default_factory=list)
    deficit_classes: list[str] = Field(default_factory=list)


class CoverageHistoryPoint(BaseModel):
    year: int
    mean_coverage: float | None
    mean_deficit: float | None
    records: int


class CoverageHistorySeries(BaseModel):
    key: str = Field(description="'all' ou o código do município.")
    label: str
    points: list[CoverageHistoryPoint]


class CoverageHistoryResponse(BaseModel):
    status: DataStatus
    message: str | None = None
    series: list[CoverageHistorySeries] = Field(default_factory=list)
