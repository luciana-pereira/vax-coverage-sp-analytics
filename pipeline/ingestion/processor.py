from __future__ import annotations

from pathlib import Path

import pandas as pd

from pipeline.config import load_settings
from pipeline.transform.transformer import attach_target_population
from pipeline.validate.validator import validate_population_alignment

from .csv_reader import read_pni_csv
from .filter import filter_pni_chunk


def _aggregate_pni_records(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega registros do PNI no contrato canônico do pipeline."""

    if df.empty:
        return pd.DataFrame(
            columns=[
                "municipality_code",
                "municipality_name",
                "immunizer",
                "year",
                "doses",
            ]
        )

    result = df.copy()

    result["year"] = pd.to_datetime(
        result["dt_vacina"],
        errors="coerce",
    ).dt.year

    result["doses"] = 1

    result = result.rename(
        columns={
            "co_municipio_paciente": "municipality_code",
            "no_municipio_paciente": "municipality_name",
            "sg_imunobiologico": "immunizer",
        }
    )

    result = result.dropna(
        subset=[
            "municipality_code",
            "year",
            "immunizer",
        ]
    )

    return result.groupby(
        [
            "municipality_code",
            "municipality_name",
            "immunizer",
            "year",
        ],
        as_index=False,
    )["doses"].sum()


def _attach_population(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Anexa a população municipal do IBGE aos dados agregados do PNI."""

    if df.empty:
        return df

    settings = load_settings()
    if not settings.population_path.is_file():
        raise RuntimeError(
            "Denominador de população-alvo ausente: "
            f"{settings.population_path}. A população municipal total do SIDRA "
            "não será usada como denominador vacinal."
        )

    population = pd.read_csv(settings.population_path)

    result = attach_target_population(df, population)
    issues = validate_population_alignment(result, population)
    if issues:
        raise RuntimeError("Ingestão CSV sem denominadores válidos: " + "; ".join(issues))
    return result


def process_pni_csv(
    path: Path,
    uf: str = "SP",
    chunksize: int = 100_000,
) -> pd.DataFrame:
    """Processa um CSV mensal do PNI em chunks."""

    filtered_chunks: list[pd.DataFrame] = []

    for chunk in read_pni_csv(path, chunksize=chunksize):
        filtered = filter_pni_chunk(chunk, uf=uf)

        if not filtered.empty:
            filtered_chunks.append(filtered)

    if not filtered_chunks:
        return pd.DataFrame()

    combined = pd.concat(filtered_chunks, ignore_index=True)

    return _aggregate_pni_records(combined)


def process_pni_files(
    paths: list[Path],
    uf: str = "SP",
    chunksize: int = 100_000,
) -> pd.DataFrame:
    """Processa todos os CSVs PNI encontrados."""

    processed: list[pd.DataFrame] = []

    for path in paths:
        result = process_pni_csv(
            path,
            uf=uf,
            chunksize=chunksize,
        )

        if not result.empty:
            processed.append(result)

    if not processed:
        return pd.DataFrame()

    combined = pd.concat(processed, ignore_index=True)

    aggregated = combined.groupby(
        [
            "municipality_code",
            "municipality_name",
            "immunizer",
            "year",
        ],
        as_index=False,
    )["doses"].sum()

    return _attach_population(aggregated)
