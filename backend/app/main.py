"""Aplicação FastAPI."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1.router import api_router
from .core.config import get_settings
from .core.errors import NotFoundError
from .core.logging import configure_logging

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", uuid4().hex)


def _error_response(request: Request, status_code: int, detail: str) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    vercel_preview = "https://*.vercel.app"
    origins = [origin for origin in settings.cors_origins if origin != vercel_preview]
    origin_regex = (
        r"https://[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.vercel\.app"
        if vercel_preview in settings.cors_origins
        else None
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API do dashboard de cobertura vacinal do Estado de São Paulo (PI IV - UNIVESP). "
            "Os contratos abaixo são a fonte de verdade da API."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=origin_regex,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(request, 404, str(exc))

    @app.exception_handler(FileNotFoundError)
    async def missing_file_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        logger.warning(
            "Arquivo necessário não encontrado request_id=%s: %s", _request_id(request), exc
        )
        return _error_response(
            request, 404, "A base de dados ainda não foi carregada ou inicializada."
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, _: RequestValidationError) -> JSONResponse:
        return _error_response(request, 422, "Parâmetros ou dados inválidos.")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        defaults = {
            400: "Requisição inválida.",
            401: "Autenticação necessária.",
            403: "Acesso não autorizado.",
            404: "Recurso não encontrado.",
            409: "Conflito com o estado atual.",
            422: "Parâmetros ou dados inválidos.",
            429: "Limite de solicitações excedido.",
        }
        detail = exc.detail
        if (
            exc.status_code < 500
            and isinstance(detail, str)
            and len(detail) <= 200
            and not any(
                marker in detail.lower()
                for marker in ("traceback", "stack trace", "file \"")
            )
        ):
            message = detail
        else:
            message = defaults.get(exc.status_code, "Não foi possível concluir a solicitação.")
        response = _error_response(request, exc.status_code, message)
        if exc.headers:
            for name, value in exc.headers.items():
                response.headers[name] = value
        return response

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        logger.exception("Erro inesperado na API request_id=%s", request_id, exc_info=exc)
        return _error_response(
            request,
            500,
            "Erro interno do serviço. Tente novamente mais tarde.",
        )

    app.include_router(api_router)
    return app


app = create_app()
