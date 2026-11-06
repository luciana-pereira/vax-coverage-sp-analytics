"""Contratos públicos para análises agregadas de doses aplicadas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AnalyticsVaccineFilter(BaseModel):
    key: str
    code: str | None = None
    abbreviation: str | None = None
    description: str | None = None
    label: str


class AnalyticsMunicipalityFilter(BaseModel):
    code: str
    name: str | None = None


class AnalyticsFilters(BaseModel):
    years: list[int] = Field(default_factory=list)
    vaccines: list[AnalyticsVaccineFilter] = Field(default_factory=list)
    age_groups: list[str] = Field(default_factory=list)
    patient_municipalities: list[AnalyticsMunicipalityFilter] = Field(default_factory=list)
    application_municipalities: list[AnalyticsMunicipalityFilter] = Field(default_factory=list)


class AnalyticsMonth(BaseModel):
    month: str
    doses: int


class AnalyticsCategory(BaseModel):
    key: str
    label: str
    doses: int


class AnalyticsVaccineCount(AnalyticsVaccineFilter):
    doses: int


class AnalyticsMunicipalityCount(AnalyticsMunicipalityFilter):
    doses: int


class VaccinationAnalyticsResponse(BaseModel):
    status: Literal["ok", "data_unavailable"]
    message: str | None = None
    source: str | None = None
    source_updated_at: datetime | None = None
    generated_at: datetime
    year: int | None = None
    period_start: str | None = None
    period_end: str | None = None
    total_doses: int = 0
    statewide: bool = False
    dimensions: dict[str, bool] = Field(default_factory=dict)
    filters: AnalyticsFilters = Field(default_factory=AnalyticsFilters)
    monthly: list[AnalyticsMonth] = Field(default_factory=list)
    by_sex: list[AnalyticsCategory] = Field(default_factory=list)
    by_age_group: list[AnalyticsCategory] = Field(default_factory=list)
    by_vaccine: list[AnalyticsVaccineCount] = Field(default_factory=list)
    by_patient_municipality: list[AnalyticsMunicipalityCount] = Field(default_factory=list)
    by_application_municipality: list[AnalyticsMunicipalityCount] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalyticsUploadResponse(VaccinationAnalyticsResponse):
    accepted_rows: int = 0
    source_token: str | None = None
