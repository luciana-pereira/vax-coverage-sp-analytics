"""Dependências injetáveis (composição de repositories e services)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query

from ..core.config import Settings, get_settings
from ..repositories.artifact_repository import ArtifactRepository
from ..repositories.coverage_repository import (
    CoverageFilter,
    CoverageRepository,
    PredictionRepository,
)
from ..services.coverage_service import CoverageService
from ..services.data_quality_service import DataQualityService
from ..services.geo_service import GeoService
from ..services.model_service import ModelService
from ..services.municipality_service import MunicipalityService
from ..services.prediction_service import PredictionService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_coverage_repository(settings: SettingsDep) -> CoverageRepository:
    return CoverageRepository(settings.features_path)


def get_artifact_repository(settings: SettingsDep) -> ArtifactRepository:
    return ArtifactRepository(settings.data_dir.parent)


CoverageRepoDep = Annotated[CoverageRepository, Depends(get_coverage_repository)]


def get_coverage_service(repo: CoverageRepoDep) -> CoverageService:
    return CoverageService(repo)


def get_municipality_service(repo: CoverageRepoDep) -> MunicipalityService:
    return MunicipalityService(repo)


def get_prediction_service(settings: SettingsDep) -> PredictionService:
    return PredictionService(
        PredictionRepository(settings.ml_dataset_path), settings.model_path, settings.metrics_path
    )


def get_model_service(
    settings: SettingsDep,
    artifacts: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
) -> ModelService:
    return ModelService(artifacts, settings.metrics_path)


def get_data_quality_service(
    settings: SettingsDep,
    repo: CoverageRepoDep,
    artifacts: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
) -> DataQualityService:
    return DataQualityService(settings, repo, artifacts)


def get_geo_service(settings: SettingsDep) -> GeoService:
    return GeoService(settings.geojson_path, settings.geojson_code_property)


def coverage_filter(
    year: Annotated[int | None, Query(description="Ano exato.", ge=1900, le=2100)] = None,
    year_from: Annotated[int | None, Query(description="Ano inicial.", ge=1900, le=2100)] = None,
    year_to: Annotated[int | None, Query(description="Ano final.", ge=1900, le=2100)] = None,
    immunizer: Annotated[str | None, Query(description="Imunizante.")] = None,
    municipality_code: Annotated[
        list[str] | None, Query(description="Código(s) do município; repita o parâmetro.")
    ] = None,
    deficit_class: Annotated[
        str | None, Query(description="Classe de déficit das linhas (baixo/moderado/alto).")
    ] = None,
) -> CoverageFilter:
    return CoverageFilter(
        year=year,
        year_from=year_from,
        year_to=year_to,
        immunizer=immunizer,
        municipality_codes=municipality_code or [],
        deficit_class=deficit_class,
    )


FilterDep = Annotated[CoverageFilter, Depends(coverage_filter)]
