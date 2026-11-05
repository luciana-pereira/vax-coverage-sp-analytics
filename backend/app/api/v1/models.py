from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ...schemas.model import ModelResponse
from ...services.model_service import ModelService
from ..deps import get_model_service

router = APIRouter(prefix="/models", tags=["models"])


@router.get(
    "",
    response_model=ModelResponse,
    summary="Avaliação dos modelos treinados",
    description=(
        "Relatório do último treino: alvo, atributos, divisão temporal, métricas por modelo "
        "(F1, precision, recall, matriz de confusão), baseline e importância das features. "
        "Retorna `not_trained` se o treino ainda não foi executado."
    ),
)
def get_models(service: Annotated[ModelService, Depends(get_model_service)]) -> ModelResponse:
    return service.report()
