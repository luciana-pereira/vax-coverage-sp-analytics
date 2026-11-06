"""Fixtures de teste.

Os dados abaixo são sintéticos e existem apenas para exercitar o código em
diretórios temporários; nunca são gravados em `data/` nem representam a fonte
real (PNI/IBGE). Nomes de colunas "da fonte" são arbitrários nos testes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

YEARS = list(range(2019, 2024))

# Variáveis de um .env local que não podem vazar para os testes.
PATH_ENV_VARS = (
    "FEATURES_PATH",
    "ML_DATASET_PATH",
    "MODEL_PATH",
    "METRICS_PATH",
    "DUCKDB_PATH",
    "COLUMN_MAPPING_PATH",
    "TARGET_POPULATION_PATH",
    "COVERAGE_TARGETS_PATH",
    "GEOJSON_PATH",
    "RAW_FILE_NAME",
    "DEDUPLICATE_RAW",
    "COVERAGE_TARGET_DEFAULT",
    "GEOJSON_CODE_PROPERTY",
)


def make_processed_frame(n_municipalities: int = 24, years: list[int] = YEARS) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    rows = []
    for m in range(n_municipalities):
        base = 60 + (m % 4) * 15
        for immunizer in ("VAC_A", "VAC_B"):
            for step, year in enumerate(years):
                ratio = np.clip(base + step * 0.8, 40, 120) / 100
                population = int(rng.integers(500, 5000))
                rows.append(
                    {
                        "municipality_code": f"35{m:05d}",
                        "municipality_name": f"Municipio {m}",
                        "immunizer": immunizer,
                        "year": year,
                        "doses": int(population * ratio),
                        "population": population,
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture
def processed_frame() -> pd.DataFrame:
    return make_processed_frame()


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Diretório `data/` temporário, apontado por DATA_DIR para todos os módulos."""
    path = tmp_path / "data"
    for sub in ("raw", "processed", "external", "models"):
        (path / sub).mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(path))
    for name in PATH_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return path


@pytest.fixture
def api_client(data_dir):
    from fastapi.testclient import TestClient

    from app.core.config import build_settings, get_settings
    from app.main import create_app

    settings = build_settings()
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)
