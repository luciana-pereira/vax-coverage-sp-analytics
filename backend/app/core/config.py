"""Configuração do backend, lida de variáveis de ambiente."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# backend/app/core/config.py -> raiz do monorepo (ou /app no contêiner).
ROOT = Path(__file__).resolve().parents[3]

load_dotenv(ROOT / ".env")


def _path(name: str, default: Path) -> Path:
    value = Path(os.getenv(name, str(default)))
    return value if value.is_absolute() else ROOT / value


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    app_env: str
    log_level: str
    cors_origins: list[str]
    data_dir: Path
    raw_dir: Path
    analytics_db_path: Path | None
    processed_file: Path
    duckdb_path: Path
    features_path: Path
    ml_dataset_path: Path
    model_path: Path
    metrics_path: Path
    geojson_path: Path
    geojson_code_property: str
    population_path: Path
    column_mapping_path: Path
    coverage_targets_path: Path


def build_settings() -> Settings:
    data_dir = _path("DATA_DIR", ROOT / "data")
    return Settings(
        app_name="Vax Coverage SP Analytics API",
        app_version="0.1.0",
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        cors_origins=_list("CORS_ORIGINS", "http://localhost:4200"),
        data_dir=data_dir,
        raw_dir=data_dir / "raw",
        analytics_db_path=(
            _path("ANALYTICS_DB_PATH", ROOT).resolve() if os.getenv("ANALYTICS_DB_PATH") else None
        ),
        processed_file=data_dir / "processed" / "vaccination.parquet",
        duckdb_path=_path("DUCKDB_PATH", data_dir / "processed" / "vax.duckdb"),
        features_path=_path("FEATURES_PATH", data_dir / "processed" / "features.parquet"),
        ml_dataset_path=_path("ML_DATASET_PATH", data_dir / "processed" / "ml_dataset.parquet"),
        model_path=_path("MODEL_PATH", data_dir / "models" / "vax_deficit_model.joblib"),
        metrics_path=_path("METRICS_PATH", data_dir / "models" / "metrics.json"),
        geojson_path=_path("GEOJSON_PATH", data_dir / "external" / "sp_municipios.geojson"),
        geojson_code_property=os.getenv("GEOJSON_CODE_PROPERTY", ""),
        population_path=_path(
            "TARGET_POPULATION_PATH", data_dir / "external" / "target_population.csv"
        ),
        column_mapping_path=_path(
            "COLUMN_MAPPING_PATH", data_dir / "external" / "column_mapping.json"
        ),
        coverage_targets_path=_path(
            "COVERAGE_TARGETS_PATH", data_dir / "external" / "coverage_targets.json"
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return build_settings()
