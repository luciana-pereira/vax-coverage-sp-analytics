"""CLI do pipeline de dados: extract -> validate -> transform -> load.

Uso: python -m pipeline.cli <extract|validate|transform|load>
Etapas de features/treino/avaliação/predição ficam em `python -m ml.cli`.
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from .config import REQUIRED_COLUMNS, PipelineSettings, load_column_mapping, load_settings
from .extract.extractor import extract_paginated
from .load.database import save_dataframe
from .transform.transformer import (
    apply_column_mapping,
    attach_target_population,
    load_jsonl,
    transform,
)
from .validate.validator import validate_dataset

logger = logging.getLogger("pipeline")

def load_pni_jsonl(path, target_uf: str = "SP"):
    df = load_jsonl(path)

    date_column = next(
        (column for column in ("dt_vacina", "data_vacina") if column in df.columns),
        None,
    )
    if date_column:
        df["year"] = pd.to_datetime(
            df[date_column],
            errors="coerce",
        ).dt.year

    if "doses" not in df.columns and "codigo_documento" in df.columns:
        df["doses"] = 1

    if "sigla_uf_paciente" in df.columns:
        patient_uf = df["sigla_uf_paciente"].astype("string").str.upper()
        df = df.loc[patient_uf == target_uf.upper()].copy()

    return df

def cmd_extract(settings: PipelineSettings, year: int) -> None:
    endpoint = f"/vacinacao/doses-aplicadas-pni-{year}"

    total = extract_paginated(
        settings.pni_api_base_url,
        endpoint,
        settings.raw_file,
        limit=settings.api_limit,
        timeout=settings.api_timeout,
    )

    logger.info(
        "Extração concluída: ano=%s registros=%s arquivo=%s",
        year,
        total,
        settings.raw_file,
    )


def cmd_transform(settings: PipelineSettings) -> None:
    if not settings.raw_file.exists():
        raise FileNotFoundError(f"Dados brutos ausentes: {settings.raw_file}. Execute 'extract'.")
    mapping = load_column_mapping(settings.column_mapping_path)
    if not mapping:
        raise RuntimeError(
            "Mapeamento de colunas ausente: "
            f"{settings.column_mapping_path}. Mapeie as colunas reais da fonte para o "
            "esquema canônico (veja docs/data/pipeline.md); o schema não é presumido."
        )

    df = transform(
        load_pni_jsonl(settings.raw_file, target_uf=settings.target_uf),
        deduplicate=settings.deduplicate_raw,
    )
    df = apply_column_mapping(df, mapping)

    if "population" not in df.columns:
        if not settings.population_path.is_file():
            raise RuntimeError(
                "Denominador de população-alvo ausente: "
                f"{settings.population_path}. A população municipal total do SIDRA "
                "não será usada como denominador vacinal."
            )

        population = pd.read_csv(settings.population_path)
        df = attach_target_population(df, population)

    settings.processed_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(settings.processed_file, index=False)
    logger.info("Processado: %s linhas em %s", len(df), settings.processed_file)


def cmd_validate(settings: PipelineSettings) -> None:
    if not settings.processed_file.exists():
        raise FileNotFoundError(f"Dados processados ausentes: {settings.processed_file}")
    report = validate_dataset(pd.read_parquet(settings.processed_file), REQUIRED_COLUMNS)
    logger.info("Linhas=%s nulos=%s", report.rows, report.null_counts)
    if not report.ok:
        for issue in report.issues:
            logger.error("Validação: %s", issue)
        raise SystemExit(1)
    logger.info("Validação concluída sem problemas.")


def cmd_load(settings: PipelineSettings) -> None:
    if not settings.processed_file.exists():
        raise FileNotFoundError(f"Dados processados ausentes: {settings.processed_file}")
    df = pd.read_parquet(settings.processed_file)
    save_dataframe(df, settings.duckdb_path, "vaccination")
    logger.info("Tabela 'vaccination' (%s linhas) em %s", len(df), settings.duckdb_path)


COMMANDS = {
    "extract": cmd_extract,
    "validate": cmd_validate,
    "transform": cmd_transform,
    "load": cmd_load,
}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--year", type=int, help="Ano dos dados a serem processados.")
    args = parser.parse_args(argv)
    try:
        settings = load_settings()

        if args.command == "extract":
            if args.year is None:
                parser.error("o comando 'extract' exige --year.")
            COMMANDS[args.command](settings, args.year)
        else:
            COMMANDS[args.command](settings)
    except (FileNotFoundError, RuntimeError, KeyError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
