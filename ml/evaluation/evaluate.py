"""Métricas de classificação e leitura do relatório de avaliação."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def classification_metrics(y_true: pd.Series, y_pred: Any, labels: list[str]) -> dict[str, Any]:
    """Accuracy, precision, recall, F1 (macro e ponderado) e matriz de confusão."""
    kwargs = {"labels": labels, "zero_division": 0}
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", **kwargs)),
        "precision_weighted": float(precision_score(y_true, y_pred, average="weighted", **kwargs)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", **kwargs)),
        "recall_weighted": float(recall_score(y_true, y_pred, average="weighted", **kwargs)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", **kwargs)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", **kwargs)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def load_metrics(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
