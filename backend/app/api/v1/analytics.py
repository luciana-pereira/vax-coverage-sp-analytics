"""Análises agregadas e upload efêmero de CSV de vacinação."""

from __future__ import annotations

import time
from secrets import token_urlsafe
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...core.config import Settings, get_settings
from ...repositories.vaccination_analytics_repository import (
    MAX_UPLOAD_BYTES,
    AnalyticsSnapshot,
    VaccinationAnalyticsRepository,
)
from ...schemas.analytics import AnalyticsUploadResponse, VaccinationAnalyticsResponse
from ...schemas.common import ErrorResponse
from ...services.vaccination_analytics_service import VaccinationAnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
UPLOAD_TTL_SECONDS = 1800


def get_analytics_service(settings: SettingsDep) -> VaccinationAnalyticsService:
    return VaccinationAnalyticsService(
        VaccinationAnalyticsRepository(settings.raw_dir, settings.analytics_db_path)
    )


AnalyticsServiceDep = Annotated[VaccinationAnalyticsService, Depends(get_analytics_service)]


@router.get(
    "",
    summary="Doses agregadas por período e dimensões",
    description=(
        "Retorna agregados mensais, por sexo, faixa etária, vacina e município. "
        "Município do paciente e município do estabelecimento permanecem separados. "
        "Identificadores pessoais e linhas individuais nunca são retornados."
    ),
    responses={
        404: {
            "model": ErrorResponse,
            "description": "A base de dados ainda não foi carregada ou inicializada.",
        },
        410: {"description": "A sessão de CSV expirou."},
    },
)
def get_analytics(
    request: Request,
    service: AnalyticsServiceDep,
    year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    vaccine: Annotated[str | None, Query(max_length=500)] = None,
    age_group: Annotated[Literal["0-4", "60+"] | None, Query()] = None,
    municipality_code: Annotated[str | None, Query(max_length=10)] = None,
    municipality_basis: Literal["patient", "application"] = "patient",
    source_token: Annotated[str | None, Query(max_length=64)] = None,
) -> VaccinationAnalyticsResponse:
    snapshot = None
    if source_token:
        cache = getattr(request.app.state, "analytics_uploads", {})
        item = cache.get(source_token)
        if item is None or item[0] <= time.monotonic():
            cache.pop(source_token, None)
            raise HTTPException(
                status_code=410,
                detail="A sessão do CSV expirou. Envie o arquivo novamente.",
            )
        snapshot = item[1]
    return service.analytics(
        year, vaccine, age_group, municipality_code, municipality_basis, snapshot
    )


def _cache_snapshot(request: Request, snapshot: AnalyticsSnapshot) -> str:
    cache = getattr(request.app.state, "analytics_uploads", None)
    if cache is None:
        cache = {}
        request.app.state.analytics_uploads = cache
    now = time.monotonic()
    expired_tokens = [token for token, (expires_at, _) in cache.items() if expires_at <= now]
    for token in expired_tokens:
        cache.pop(token, None)
    while len(cache) >= 5:
        cache.pop(next(iter(cache)))
    source_token = token_urlsafe(32)
    cache[source_token] = (now + UPLOAD_TTL_SECONDS, snapshot)
    return source_token


@router.post(
    "/pni",
    summary="Atualizar agregados pela API PNI configurada",
    description=(
        "Consulta páginas da API PNI e agrega no backend. Os registros individuais da resposta, "
        "incluindo IDs, nunca são gravados nem retornados. A operação pode ser demorada."
    ),
    responses={502: {"description": "A fonte PNI está indisponível ou retornou dados inválidos."}},
)
def refresh_pni(
    request: Request,
    service: AnalyticsServiceDep,
    year: Annotated[int, Query(ge=2000, le=2100)] = 2024,
) -> AnalyticsUploadResponse:
    try:
        snapshot = service.repository.pni_api_snapshot(year)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    source_token = _cache_snapshot(request, snapshot)
    response = service.analytics(year=year, snapshot=snapshot)
    return AnalyticsUploadResponse(
        **response.model_dump(), accepted_rows=snapshot.total_rows, source_token=source_token
    )


@router.post(
    "/upload",
    summary="Validar e agregar CSV de vacinação",
    description=(
        "Aceita CSV de até 25 MiB e 500.000 linhas, agrega em memória e retorna somente "
        "contagens. O conteúdo individual não é gravado nem enviado ao frontend."
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
    responses={
        413: {"description": "CSV excede o limite."},
        415: {"description": "Tipo de conteúdo inválido."},
        422: {"description": "Nome, schema, encoding ou conteúdo inválido."},
    },
)
async def upload_csv(
    request: Request,
    service: AnalyticsServiceDep,
) -> AnalyticsUploadResponse:
    filename = request.headers.get("x-file-name", "")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Envie um arquivo com extensão .csv.")
    if content_type not in {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="O conteúdo enviado deve ser CSV.")
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="O CSV excede o limite de 25 MiB.")
    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="O CSV excede o limite de 25 MiB.")
        chunks.extend(chunk)
    content = bytes(chunks)
    try:
        snapshot = service.repository.csv_snapshot(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    source_token = _cache_snapshot(request, snapshot)
    response = service.analytics(snapshot=snapshot)
    return AnalyticsUploadResponse(
        **response.model_dump(), accepted_rows=snapshot.total_rows, source_token=source_token
    )
