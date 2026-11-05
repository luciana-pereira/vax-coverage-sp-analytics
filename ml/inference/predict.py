"""Inferência com o modelo treinado (separada do treinamento)."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd


def load_model(model_path: Path):
    return joblib.load(model_path)


def load_feature_list(metrics_path: Path) -> list[str]:
    """Atributos esperados pelo modelo, registrados no relatório do treino."""
    return list(json.loads(metrics_path.read_text(encoding="utf-8"))["features"])


def predict(model_path, df: pd.DataFrame) -> pd.Series:
    model = joblib.load(model_path)
    return pd.Series(model.predict(df), index=df.index, name="prediction")


def predict_with_probabilities(model, df: pd.DataFrame) -> pd.DataFrame:
    """Classe prevista e probabilidade por classe, quando o modelo as fornece."""
    out = pd.DataFrame({"prediction": model.predict(df)}, index=df.index)
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(df)
        for position, label in enumerate(model.classes_):
            out[f"proba_{label}"] = proba[:, position]
    return out
