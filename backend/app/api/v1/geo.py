from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ...schemas.common import SERVER_ERROR_RESPONSES
from ...schemas.data_quality import GeoResponse
from ...services.geo_service import GeoService
from ..deps import get_geo_service

router = APIRouter(prefix="/geo", tags=["geo"], responses=SERVER_ERROR_RESPONSES)


@router.get(
    "/municipalities",
    response_model=GeoResponse,
    summary="GeoJSON dos municípios de São Paulo",
    description=(
        "Entrega o GeoJSON configurado em `GEOJSON_PATH`. O projeto não inclui geometrias: "
        "sem o arquivo, retorna `data_unavailable`."
    ),
)
def get_geo_municipalities(
    service: Annotated[GeoService, Depends(get_geo_service)],
) -> GeoResponse:
    return service.municipalities()
