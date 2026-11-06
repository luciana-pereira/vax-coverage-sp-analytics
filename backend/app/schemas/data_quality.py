"""Schemas de qualidade de dados e dados geográficos."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .common import DataStatus


class ArtifactStatus(BaseModel):
    name: str
    description: str
    path: str = Field(description="Caminho relativo à raiz do projeto.")
    exists: bool
    size_bytes: int | None = None


class ColumnQuality(BaseModel):
    name: str
    null_count: int
    null_ratio: float


class YearRecordCount(BaseModel):
    year: int
    records: int


class DatasetQuality(BaseModel):
    rows: int
    municipalities: int | None = None
    year_min: int | None = None
    year_max: int | None = None
    duplicate_rows: int
    missing_columns: list[str] = Field(description="Colunas esperadas ausentes.")
    columns: list[ColumnQuality]
    records_by_year: list[YearRecordCount] = Field(default_factory=list)


class DataQualityResponse(BaseModel):
    status: DataStatus
    artifacts: list[ArtifactStatus]
    dataset: DatasetQuality | None = None
    known_gaps: list[str] = Field(description="Dependências ainda não atendidas.")


class GeoResponse(BaseModel):
    status: DataStatus
    message: str | None = None
    code_property: str | None = Field(
        default=None, description="Propriedade do GeoJSON com o código do município."
    )
    feature_count: int = 0
    geojson: dict | None = Field(default=None, description="FeatureCollection GeoJSON.")
