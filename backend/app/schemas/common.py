"""Schemas compartilhados entre os endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DataStatus = Literal["ok", "data_unavailable"]


class ErrorResponse(BaseModel):
    detail: str = Field(description="Descrição do erro.", examples=["Município não encontrado."])


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(description="Estado do serviço.")
    app: str = Field(description="Nome da aplicação.")
    version: str = Field(description="Versão da API.")
    environment: str = Field(description="Ambiente de execução.")
