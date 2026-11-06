from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ...schemas.common import QUERY_ERROR_RESPONSES
from ...schemas.coverage import (
    CoverageByImmunizerResponse,
    CoverageFilterOptions,
    CoverageHistoryResponse,
    CoverageResponse,
)
from ...services.coverage_service import CoverageService
from ..deps import FilterDep, get_coverage_service

router = APIRouter(prefix="/coverage", tags=["coverage"], responses=QUERY_ERROR_RESPONSES)

ServiceDep = Annotated[CoverageService, Depends(get_coverage_service)]


@router.get(
    "",
    response_model=CoverageResponse,
    summary="Indicadores de cobertura e déficit",
    description=(
        "KPIs agregados (cobertura média, déficit médio, municípios abaixo da meta e críticos), "
        "distribuição por classe de déficit e ranking de municípios com maior déficit médio. "
        "Médias simples sobre as linhas filtradas. Sem dataset, retorna `data_unavailable`."
    ),
)
def get_coverage(
    service: ServiceDep,
    flt: FilterDep,
    ranking_limit: Annotated[int, Query(ge=1, le=100, description="Itens do ranking.")] = 10,
) -> CoverageResponse:
    return service.overview(flt, ranking_limit)


@router.get(
    "/filters",
    response_model=CoverageFilterOptions,
    summary="Valores disponíveis para os filtros",
    description="Anos, imunizantes (se a coluna existir) e classes de déficit presentes nos dados.",
)
def get_filters(service: ServiceDep) -> CoverageFilterOptions:
    return service.filter_options()


@router.get(
    "/immunizers",
    response_model=CoverageByImmunizerResponse,
    summary="Cobertura e déficit por imunizante",
    description=(
        "Agrega cobertura e déficit médios por imunizante usando os filtros aplicados. "
        "Sem dimensões vacinais ou dataset válido, retorna `data_unavailable`."
    ),
)
def get_coverage_by_immunizer(service: ServiceDep, flt: FilterDep) -> CoverageByImmunizerResponse:
    return service.by_immunizer(flt)


@router.get(
    "/history",
    response_model=CoverageHistoryResponse,
    summary="Série histórica de cobertura e déficit",
    description=(
        "Evolução anual. Sem `municipality_code`, uma série agregada (`all`). "
        "Com um ou mais `municipality_code`, uma série por município (comparação)."
    ),
)
def get_history(service: ServiceDep, flt: FilterDep) -> CoverageHistoryResponse:
    return service.history(flt)
