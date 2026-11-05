from __future__ import annotations

from fastapi import APIRouter

from ...schemas.common import HealthResponse
from ..deps import SettingsDep

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verifica o estado da API",
    description="Retorna `ok` quando o serviço está em execução. Não consulta os dados.",
)
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
