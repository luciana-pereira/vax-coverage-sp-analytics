"""Treinamento com validação temporal e comparação dos modelos candidatos."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from ml.evaluation.evaluate import classification_metrics
from ml.models.preprocessing import to_object_nan
from ml.models.registry import build_candidates

SELECTION_CRITERION = "f1_macro"
TOP_FEATURES = 20


def _preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    categorical = X.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    numeric = [c for c in X.columns if c not in categorical]
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]
                ),
                numeric,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("nan", FunctionTransformer(to_object_nan, feature_names_out="one-to-one")),
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
        ]
    )


def _fit(estimator: Any, train: pd.DataFrame, features: list[str], target: str) -> Pipeline:
    X = train[features]
    pipe = Pipeline([("preprocessor", _preprocessor(X)), ("model", clone(estimator))])
    pipe.fit(X, train[target].astype(str))
    return pipe


def _feature_importance(pipe: Pipeline) -> list[dict[str, float]]:
    names = pipe.named_steps["preprocessor"].get_feature_names_out()
    model = pipe.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        values = np.abs(np.asarray(model.coef_, dtype=float)).mean(axis=0)
    else:
        return []
    order = np.argsort(values)[::-1][:TOP_FEATURES]
    return [{"feature": str(names[i]), "importance": float(values[i])} for i in order]


def _split_years(years: list[int]) -> tuple[list[int], int | None, int]:
    test_year = years[-1]
    if len(years) >= 3:
        return years[:-2], years[-2], test_year
    return years[:-1], None, test_year


def train_models(
    df: pd.DataFrame,
    features: list[str],
    target: str,
    year_col: str,
    model_path: Path,
    metrics_path: Path,
    class_order: Sequence[str] | None = None,
    baseline_col: str | None = None,
    random_state: int = 42,
) -> dict[str, Any]:
    """Treina os candidatos com validação temporal e persiste o melhor modelo.

    Com 3+ períodos: treino < validação < teste; o modelo é escolhido pelo F1
    macro na validação e reavaliado no teste (treinado com treino+validação).
    Com 2 períodos não há validação separada e a escolha usa o teste, o que é
    registrado em `selection`.
    """
    data = df.dropna(subset=[target, year_col]).copy()
    data[year_col] = pd.to_numeric(data[year_col], errors="coerce")
    data = data.dropna(subset=[year_col])
    data[year_col] = data[year_col].astype(int)

    years = sorted(int(y) for y in data[year_col].unique())
    if len(years) < 2:
        raise ValueError("São necessários pelo menos dois períodos para validação temporal.")

    present = set(data[target].astype(str))
    labels = [c for c in (class_order or []) if c in present]
    labels += sorted(present - set(labels))

    train_years, val_year, test_year = _split_years(years)
    train = data[data[year_col].isin(train_years)]
    validation = data[data[year_col] == val_year] if val_year is not None else None
    test = data[data[year_col] == test_year]
    full_train = data[data[year_col] < test_year]
    if train[target].nunique() < 2 or full_train[target].nunique() < 2:
        raise ValueError("O treino precisa de ao menos duas classes distintas.")

    results: dict[str, Any] = {}
    fitted: dict[str, Pipeline] = {}
    scores: dict[str, float] = {}

    for name, estimator in build_candidates(random_state).items():
        entry: dict[str, Any] = {"validation": None}
        if validation is not None and not validation.empty:
            val_pipe = _fit(estimator, train, features, target)
            entry["validation"] = classification_metrics(
                validation[target].astype(str), val_pipe.predict(validation[features]), labels
            )
        final = _fit(estimator, full_train, features, target)
        entry["test"] = classification_metrics(
            test[target].astype(str), final.predict(test[features]), labels
        )
        results[name] = entry
        fitted[name] = final
        source = entry["validation"] or entry["test"]
        scores[name] = source[SELECTION_CRITERION]

    best_name = max(scores, key=scores.get)

    baseline = None
    if baseline_col and baseline_col in test.columns:
        fallback = full_train[target].astype(str).mode().iloc[0]
        pred = test[baseline_col].astype("string").fillna(fallback).astype(str)
        baseline = {
            "description": "persistência: classe do ano t prevista como classe do ano t+1",
            "test": classification_metrics(test[target].astype(str), pred, labels),
        }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted[best_name], model_path)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "features": features,
        "classes": labels,
        "split": {
            "scheme": "temporal",
            "train_years": train_years,
            "validation_year": val_year,
            "test_year": test_year,
            "n_train": int(len(train)),
            "n_validation": int(len(validation)) if validation is not None else 0,
            "n_test": int(len(test)),
        },
        "selection": {
            "criterion": SELECTION_CRITERION,
            "split": "validation" if val_year is not None else "test",
            "note": None
            if val_year is not None
            else "Menos de 3 períodos: escolha feita no conjunto de teste (otimista).",
        },
        "best_model": best_name,
        "models": results,
        "baseline": baseline,
        "feature_importance": _feature_importance(fitted[best_name]),
    }
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
