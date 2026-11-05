"""Schemas de predição."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PredictionItem(BaseModel):
    municipality_code: str
    municipality_name: str | None = None
    immunizer: str | None = None
    source_year: int = Field(description="Ano dos atributos usados na predição.")
    predicted_class: str = Field(description="Classe de déficit prevista para o ano seguinte.")
    probabilities: dict[str, float] | None = Field(
        default=None, description="Probabilidade por classe, se o modelo as fornece."
    )


class PredictionResponse(BaseModel):
    status: Literal["ok", "model_unavailable", "data_unavailable"]
    message: str | None = None
    model_name: str | None = None
    source_year: int | None = None
    target_year: int | None = None
    total: int = 0
    class_distribution: dict[str, int] = Field(default_factory=dict)
    items: list[PredictionItem] = Field(default_factory=list)
