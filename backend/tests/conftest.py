"""Fixtures do backend: dados pequenos e explícitos em diretório temporário.

Os valores são sintéticos, escolhidos para permitir conferir as agregações à mão.
"""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, build_settings, get_settings
from app.main import create_app

FEATURE_ROWS = [
    # code, name, immunizer, year, coverage, deficit, class
    ("1100", "Alpha", "X", 2022, 90.0, 5.0, "baixo"),
    ("1100", "Alpha", "X", 2023, 80.0, 15.0, "moderado"),
    ("2200", "Beta", "X", 2022, 70.0, 25.0, "alto"),
    ("2200", "Beta", "X", 2023, 96.0, 0.0, "baixo"),
    ("3300", "Gamma", "Y", 2023, 60.0, 35.0, "alto"),
]


@pytest.fixture
def settings(tmp_path, monkeypatch) -> Settings:
    for name in (
        "FEATURES_PATH",
        "ML_DATASET_PATH",
        "MODEL_PATH",
        "METRICS_PATH",
        "COLUMN_MAPPING_PATH",
        "TARGET_POPULATION_PATH",
        "COVERAGE_TARGETS_PATH",
        "GEOJSON_PATH",
        "CORS_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("GEOJSON_CODE_PROPERTY", "")
    return build_settings()


@pytest.fixture
def make_client(settings):
    def _make() -> TestClient:
        app = create_app()
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    return _make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


@pytest.fixture
def features_file(settings):
    settings.features_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        FEATURE_ROWS,
        columns=[
            "municipality_code",
            "municipality_name",
            "immunizer",
            "year",
            "coverage",
            "deficit",
            "deficit_class",
        ],
    )
    frame.to_parquet(settings.features_path, index=False)
    return settings.features_path
