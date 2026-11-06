"""CLI do pipeline de dados: extract -> validate -> transform -> load.

Uso: python -m pipeline.cli <extract|validate|transform|load>
Etapas de features/treino/avaliação/predição ficam em `python -m ml.cli`.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from uuid import uuid4

import pandas as pd
import requests

from .config import REQUIRED_COLUMNS, PipelineSettings, load_column_mapping, load_settings
from .extract.extractor import extract_paginated
from .load.database import save_dataframe
from .transform.transformer import (
    apply_column_mapping,
    attach_target_population,
    load_jsonl,
    transform,
)
from .validate.validator import validate_dataset, validate_population_alignment

logger = logging.getLogger("pipeline")


def _write_parquet_atomically(df: pd.DataFrame, output_path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(
        f".{output_path.stem}.{uuid4().hex}.tmp{output_path.suffix}"
    )
    try:
        df.to_parquet(temporary_path, index=False)
        os.replace(temporary_path, output_path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


PNI_SOURCE_ALIASES = {
    "municipality_code": ("co_municipio_paciente", "codigo_municipio_paciente"),
    "municipality_name": ("no_municipio_paciente", "nome_municipio_paciente"),
    "immunizer": ("sg_imunobiologico", "codigo_vacina", "co_vacina"),
    "id": ("ref_uuid",),
    "immunizer_name": ("ds_vacina", "descricao_vacina"),
    "date": ("dt_vacina", "data_vacina"),
    "birth_date": ("dt_nascimento_paciente",),
    "sex": ("tp_sexo_paciente", "tipo_sexo_paciente"),
    "cnes_code": ("co_cnes_estabelecimento", "codigo_cnes_estabelecimento"),
    "facility_name": (
        "no_razao_social_estabelecimento",
        "nome_razao_social_estabelecimento",
    ),
}
OPTIONAL_PNI_MAPPING_FIELDS = {
    "id",
    "municipality_name",
    "immunizer_name",
    "date",
    "birth_date",
    "sex",
    "cnes_code",
    "facility_name",
}

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

    if "doses" not in df.columns and (
        "codigo_documento" in df.columns or "sg_imunobiologico" in df.columns
    ):
        df["doses"] = 1

    if "sigla_uf_paciente" in df.columns:
        patient_uf = df["sigla_uf_paciente"].astype("string").str.upper()
        df = df.loc[patient_uf == target_uf.upper()].copy()

    return df


def resolve_pni_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> dict[str, str]:
    """Use configured sources first, then aliases observed in PNI payloads."""
    resolved = {}
    for canonical, configured_source in mapping.items():
        if configured_source in df.columns:
            resolved[canonical] = configured_source
            continue
        source = next(
            (
                candidate
                for candidate in PNI_SOURCE_ALIASES.get(canonical, ())
                if candidate in df.columns
            ),
            None,
        )
        if source:
            resolved[canonical] = source
        elif canonical not in OPTIONAL_PNI_MAPPING_FIELDS:
            resolved[canonical] = configured_source
    return resolved


def _validate_processed_frame(df: pd.DataFrame, settings: PipelineSettings):
    report = validate_dataset(df, REQUIRED_COLUMNS)
    if not report.ok:
        return report
    if not settings.population_path.is_file():
        report.issues.append(
            "Arquivo de população-alvo ausente; não é possível validar os denominadores."
        )
        return report
    target_population = pd.read_csv(settings.population_path)
    report.issues.extend(validate_population_alignment(df, target_population))
    return report

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
    df = apply_column_mapping(df, resolve_pni_mapping(df, mapping))

    if not settings.population_path.is_file():
        raise RuntimeError(
            "Denominador de população-alvo ausente: "
            f"{settings.population_path}. A população municipal total do SIDRA "
            "não será usada como denominador vacinal."
        )
    population = pd.read_csv(settings.population_path)
    df = attach_target_population(df, population)
    report = _validate_processed_frame(df, settings)
    if not report.ok:
        raise RuntimeError(
            "Transformação inválida; o Parquet anterior foi preservado: "
            + "; ".join(report.issues)
        )

    _write_parquet_atomically(df, settings.processed_file)
    logger.info("Processado: %s linhas em %s", len(df), settings.processed_file)


def cmd_validate(settings: PipelineSettings) -> None:
    if not settings.processed_file.exists():
        raise FileNotFoundError(f"Dados processados ausentes: {settings.processed_file}")
    report = _validate_processed_frame(pd.read_parquet(settings.processed_file), settings)
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
    report = _validate_processed_frame(df, settings)
    if not report.ok:
        raise RuntimeError(
            "Dataset processado inválido; a tabela DuckDB não foi atualizada: "
            + "; ".join(report.issues)
        )
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
    except (requests.RequestException, OSError) as exc:
        logger.error("Falha na etapa '%s' ao acessar a fonte ou os arquivos: %s", args.command, exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
