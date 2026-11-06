from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ...schemas.common import SERVER_ERROR_RESPONSES
from ...schemas.data_quality import DataQualityResponse
from ...services.data_quality_service import DataQualityService
from ..deps import get_data_quality_service

router = APIRouter(prefix="/data-quality", tags=["data-quality"], responses=SERVER_ERROR_RESPONSES)


@router.get(
    "",
    response_model=DataQualityResponse,
    summary="Qualidade dos dados e lacunas conhecidas",
    description=(
        "Status dos artefatos (bruto, processado, features, modelo, GeoJSON, população-alvo), "
        "qualidade do dataset de features (nulos, duplicatas, anos) e dependências pendentes."
    ),
)
def get_data_quality(
    service: Annotated[DataQualityService, Depends(get_data_quality_service)],
) -> DataQualityResponse:
    return service.report()
