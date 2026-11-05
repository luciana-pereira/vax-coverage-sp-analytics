"""Engenharia de atributos: cobertura, déficit, classe e dataset supervisionado."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

DEFICIT_BINS = [-0.01, 5, 15, float("inf")]
DEFICIT_LABELS = ["baixo", "moderado", "alto"]

TARGET_COLUMN = "deficit_class_next"
ENTITY_COLUMNS = ("municipality_code", "immunizer")

# Colunas do ano corrente usadas como atributos (o alvo é o ano seguinte).
BASE_FEATURES = ["coverage", "deficit", "doses", "population", "year"]
LAG_FEATURES = ["coverage_prev", "deficit_prev", "coverage_delta"]
CATEGORICAL_FEATURES = ["immunizer"]


def build_vaccination_features(
    df: pd.DataFrame,
    doses_col: str,
    population_col: str,
    year_col: str,
    target_col: str = "coverage_target",
    meta: float = 95.0,
    immunizer_col: str | None = None,
    targets: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Calcula `coverage`, `deficit` e `deficit_class`.

    `coverage = doses / população-alvo * 100` e
    `deficit = max(0, meta - coverage)`. A meta é `meta`, salvo se `targets`
    informar uma meta específica para o imunizante em `immunizer_col`.
    """
    out = df.copy()

    out["doses"] = pd.to_numeric(out[doses_col], errors="coerce")
    out["population"] = pd.to_numeric(out[population_col], errors="coerce")
    out["year"] = pd.to_numeric(out[year_col], errors="coerce")

    out["coverage"] = (out["doses"] / out["population"].where(out["population"] != 0)) * 100
    if targets and immunizer_col and immunizer_col in out.columns:
        out[target_col] = out[immunizer_col].map(targets).fillna(meta).astype(float)
    else:
        out[target_col] = float(meta)
    out["deficit"] = (out[target_col] - out["coverage"]).clip(lower=0)

    out["deficit_class"] = pd.cut(
        out["deficit"],
        bins=DEFICIT_BINS,
        labels=DEFICIT_LABELS,
    )

    return out


def _entity_keys(df: pd.DataFrame) -> list[str]:
    return [c for c in ENTITY_COLUMNS if c in df.columns]


def build_ml_dataset(features: pd.DataFrame) -> pd.DataFrame:
    """Dataset supervisionado: atributos do ano `t` -> classe de déficit em `t+1`.

    O alvo é a classe do período seguinte da mesma entidade, evitando que
    `deficit_class` (derivada de `coverage`/`deficit`) seja usada para predizer
    a própria classe. Linhas sem ano seguinte ficam com alvo nulo e servem à
    inferência. Atributos defasados usam o ano imediatamente anterior.
    """
    keys = _entity_keys(features)
    if not keys:
        raise KeyError("Dataset sem coluna de entidade (municipality_code/immunizer).")

    df = features.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year", "coverage"]).copy()
    df["year"] = df["year"].astype(int)
    df["deficit_class"] = df["deficit_class"].astype("string")

    nxt = df[keys + ["year", "deficit_class"]].copy()
    nxt["year"] = nxt["year"] - 1
    nxt = nxt.rename(columns={"deficit_class": TARGET_COLUMN})
    nxt = nxt.drop_duplicates(subset=keys + ["year"])

    prev = df[keys + ["year", "coverage", "deficit"]].copy()
    prev["year"] = prev["year"] + 1
    prev = prev.rename(columns={"coverage": "coverage_prev", "deficit": "deficit_prev"})
    prev = prev.drop_duplicates(subset=keys + ["year"])

    out = df.merge(nxt, on=keys + ["year"], how="left")
    out = out.merge(prev, on=keys + ["year"], how="left")
    out["coverage_delta"] = out["coverage"] - out["coverage_prev"]
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Atributos usados no treino, sem alvo nem colunas derivadas dele."""
    cols = [c for c in BASE_FEATURES + LAG_FEATURES + CATEGORICAL_FEATURES if c in df.columns]
    if "deficit_class" in cols or TARGET_COLUMN in cols:
        raise ValueError("Vazamento de alvo: classe não pode ser atributo.")
    return cols
