"""Schemas de modelos de ML."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ModelMetrics(BaseModel):
    accuracy: float
    precision_macro: float
    precision_weighted: float
    recall_macro: float
    recall_weighted: float
    f1_macro: float
    f1_weighted: float
    confusion_matrix: list[list[int]] = Field(description="Linhas = real, colunas = previsto.")


class ModelEntry(BaseModel):
    name: str
    is_best: bool
    validation: ModelMetrics | None = None
    test: ModelMetrics


class SplitInfo(BaseModel):
    scheme: str
    train_years: list[int]
    validation_year: int | None = None
    test_year: int
    n_train: int
    n_validation: int
    n_test: int


class SelectionInfo(BaseModel):
    criterion: str
    split: str
    note: str | None = None


class BaselineInfo(BaseModel):
    description: str
    test: ModelMetrics


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class ModelResponse(BaseModel):
    status: Literal["ok", "not_trained"]
    message: str | None = None
    generated_at: str | None = None
    target: str | None = None
    features: list[str] = Field(default_factory=list)
    classes: list[str] = Field(default_factory=list)
    split: SplitInfo | None = None
    selection: SelectionInfo | None = None
    best_model: str | None = None
    models: list[ModelEntry] = Field(default_factory=list)
    baseline: BaselineInfo | None = None
    feature_importance: list[FeatureImportanceItem] = Field(default_factory=list)
