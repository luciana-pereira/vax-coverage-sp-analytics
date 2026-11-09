"""Configuração do pipeline de dados, lida de variáveis de ambiente."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")

# Colunas canônicas esperadas depois da etapa de transformação.
CANONICAL_COLUMNS = (
    "id",
    "municipality_code",
    "municipality_name",
    "immunizer",
    "immunizer_name",
    "date",
    "birth_date",
    "sex",
    "cnes_code",
    "facility_name",
    "year",
    "doses",
    "population",
)
REQUIRED_COLUMNS = (
    "municipality_code",
    "immunizer",
    "year",
    "doses",
    "population",
)


def _path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else ROOT / value


def _data_path(name: str, default_relative: str, data_dir: Path) -> Path:
    value = os.getenv(name)

    if not value:
        return data_dir / default_relative

    path = Path(value)

    if path.is_absolute():
        return path

    if path.parts and path.parts[0].lower() == Path("data").name:
        path = Path(*path.parts[1:])

    return data_dir / path


@dataclass(frozen=True)
class PipelineSettings:
    pni_api_base_url: str
    ibge_sidra_base_url: str
    ibge_population_table: int
    ibge_population_variable: int
    api_limit: int
    api_timeout: int
    target_uf: str
    data_dir: Path
    raw_file: Path
    processed_file: Path
    duckdb_path: Path
    column_mapping_path: Path
    population_path: Path
    deduplicate_raw: bool


def load_settings() -> PipelineSettings:
    data_dir = _path("DATA_DIR", "data")
    return PipelineSettings(
        pni_api_base_url=os.getenv(
            "PNI_API_BASE_URL",
            "https://apidadosabertos.saude.gov.br",
        ),
        ibge_sidra_base_url=os.getenv(
            "IBGE_SIDRA_BASE_URL",
            "https://apisidra.ibge.gov.br",
        ),
        ibge_population_table=int(os.getenv("IBGE_POPULATION_TABLE", "6579")),
        ibge_population_variable=int(os.getenv("IBGE_POPULATION_VARIABLE", "9324")),
        api_limit=int(os.getenv("API_LIMIT", "1000")),
        api_timeout=int(os.getenv("API_TIMEOUT", "120")),
        target_uf=os.getenv("TARGET_UF", "SP"),
        data_dir=data_dir,
        raw_file=data_dir / "raw" / os.getenv("RAW_FILE_NAME", "pni_2024.jsonl"),
        processed_file=data_dir / "processed" / "vaccination.parquet",
        duckdb_path=_data_path(
            "DUCKDB_PATH",
            "processed/vax.duckdb",
            data_dir,
        ),
        column_mapping_path=_data_path(
            "COLUMN_MAPPING_PATH",
            "external/column_mapping.json",
            data_dir,
        ),
        population_path=_data_path(
            "TARGET_POPULATION_PATH",
            "external/target_population.csv",
            data_dir,
        ),
        deduplicate_raw=os.getenv("DEDUPLICATE_RAW", "false").lower() in {"1", "true", "yes"},
    )


def load_column_mapping(path: Path) -> dict[str, str]:
    """Lê o mapeamento `coluna_canônica -> coluna_da_fonte` (opcional)."""
    if not path.exists():
        return {}
    mapping = json.loads(path.read_text(encoding="utf-8-sig"))
    unknown = set(mapping) - set(CANONICAL_COLUMNS)
    if unknown:
        raise ValueError(f"Colunas canônicas desconhecidas no mapeamento: {sorted(unknown)}")
    return {str(k): str(v) for k, v in mapping.items()}
