from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ...schemas.prediction import PredictionResponse
from ...services.prediction_service import PredictionService
from ..deps import get_prediction_service

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get(
    "",
    response_model=PredictionResponse,
    summary="Classe de déficit prevista para o ano seguinte",
    description=(
        "Aplica o modelo treinado aos atributos do último ano sem rótulo (ou de `year`). "
        "`status` indica `model_unavailable` ou `data_unavailable` quando faltam artefatos."
    ),
)
def get_predictions(
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    year: Annotated[int | None, Query(description="Ano dos atributos (origem).")] = None,
    municipality_code: Annotated[str | None, Query()] = None,
    immunizer: Annotated[str | None, Query()] = None,
    predicted_class: Annotated[
        str | None, Query(description="Filtra pela classe prevista.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PredictionResponse:
    return service.predict(year, municipality_code, immunizer, predicted_class, limit, offset)
