from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ...schemas.common import ErrorResponse
from ...schemas.municipality import MunicipalityDetailResponse, MunicipalityListResponse
from ...services.municipality_service import MunicipalityService
from ..deps import FilterDep, get_municipality_service

router = APIRouter(prefix="/municipalities", tags=["municipalities"])

ServiceDep = Annotated[MunicipalityService, Depends(get_municipality_service)]


@router.get(
    "",
    response_model=MunicipalityListResponse,
    summary="Lista municípios com cobertura e déficit médios",
    description=(
        "Agregação por município sobre as linhas filtradas, ordenada por nome/código. "
        "Usada pelo mapa e pelo ranking. Sem dataset, retorna `data_unavailable`."
    ),
)
def list_municipalities(
    service: ServiceDep,
    flt: FilterDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MunicipalityListResponse:
    return service.list(flt, limit, offset)


@router.get(
    "/{municipality_id}",
    response_model=MunicipalityDetailResponse,
    summary="Detalhe de um município",
    description="Indicadores, histórico anual e resumo por imunizante do município (código).",
    responses={404: {"model": ErrorResponse, "description": "Município sem registros."}},
)
def get_municipality(
    municipality_id: str, service: ServiceDep, flt: FilterDep
) -> MunicipalityDetailResponse:
    return service.detail(municipality_id, flt)
