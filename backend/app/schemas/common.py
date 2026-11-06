"""Schemas compartilhados entre os endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DataStatus = Literal["ok", "data_unavailable"]


class ErrorResponse(BaseModel):
    detail: str = Field(description="Descrição do erro.", examples=["Município não encontrado."])
    request_id: str = Field(description="Identificador para correlacionar com o log do servidor.")


SERVER_ERROR_RESPONSES = {
    500: {
        "model": ErrorResponse,
        "description": "Erro interno sanitizado; use request_id para suporte.",
    },
}

QUERY_ERROR_RESPONSES = {
    **SERVER_ERROR_RESPONSES,
    422: {
        "model": ErrorResponse,
        "description": "Parâmetros ou dados inválidos.",
    },
}


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(description="Estado do serviço.")
    app: str = Field(description="Nome da aplicação.")
    version: str = Field(description="Versão da API.")
    environment: str = Field(description="Ambiente de execução.")
