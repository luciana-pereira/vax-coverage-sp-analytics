"""Fontes que retornam somente grupos agregados; nunca expõem linhas individuais."""

from __future__ import annotations

import csv
import io
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator

import duckdb
import requests

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_UPLOAD_ROWS = 500_000
EXPECTED_SP_MUNICIPALITIES = 645

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "vaccination_date": ("dt_vacina", "data_vacina", "vaccination_date"),
    "vaccine_code": ("co_vacina", "codigo_vacina", "vaccine_code"),
    "vaccine_abbreviation": ("sg_imunobiologico", "vaccine_abbreviation"),
    "vaccine_description": ("ds_vacina", "descricao_vacina", "vaccine_description"),
    "sex": ("tp_sexo_paciente", "tipo_sexo_paciente", "sex"),
    "birth_date": ("dt_nascimento_paciente", "birth_date"),
    "age": ("numero_idade_paciente", "age"),
    "patient_municipality_code": (
        "co_municipio_paciente",
        "codigo_municipio_paciente",
        "patient_municipality_code",
    ),
    "patient_municipality_name": (
        "no_municipio_paciente",
        "nome_municipio_paciente",
        "patient_municipality_name",
    ),
    "application_municipality_code": (
        "co_municipio_estabelecimento",
        "codigo_municipio_estabelecimento",
        "application_municipality_code",
    ),
    "application_municipality_name": (
        "no_municipio_estabelecimento",
        "nome_municipio_estabelecimento",
        "application_municipality_name",
    ),
    "patient_state": ("sigla_uf_paciente", "patient_state"),
    "application_state": ("sigla_uf_estabelecimento", "application_state"),
}

GROUP_FIELDS = (
    "year",
    "month",
    "vaccine_code",
    "vaccine_abbreviation",
    "vaccine_description",
    "sex",
    "age_group",
    "patient_municipality_code",
    "patient_municipality_name",
    "application_municipality_code",
    "application_municipality_name",
)


@dataclass(frozen=True)
class AnalyticsSnapshot:
    rows: tuple[dict[str, Any], ...]
    source: str
    source_updated_at: datetime | None
    total_rows: int
    statewide: bool
    dimensions: dict[str, bool]
    warnings: tuple[str, ...] = ()


def _norm(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none", "null", "<na>"} else None


def _date(value: Any) -> date | None:
    text = _norm(value)
    if text is None:
        return None
    for parser in (
        lambda: datetime.fromisoformat(text.replace("Z", "+00:00")).date(),
        lambda: datetime.strptime(text, "%d/%m/%Y").date(),
        lambda: datetime.strptime(text, "%Y%m%d").date(),
    ):
        try:
            return parser()
        except ValueError:
            continue
    return None


def _age_years(record: dict[str, Any], applied_on: date) -> int | None:
    raw_age = _norm(record.get("age"))
    if raw_age is not None:
        try:
            age = int(float(raw_age))
            return age if 0 <= age <= 120 else None
        except ValueError:
            return None
    birth_date = _date(record.get("birth_date"))
    if birth_date is None or birth_date > applied_on:
        return None
    age = applied_on.year - birth_date.year
    return age - ((applied_on.month, applied_on.day) < (birth_date.month, birth_date.day))


def _age_group(age: int | None) -> str | None:
    if age is None:
        return None
    if age <= 4:
        return "0-4"
    if age >= 60:
        return "60+"
    return "5-59"


def _vaccine_key(code: str | None, abbreviation: str | None, description: str | None) -> str:
    return json.dumps([code, abbreviation, description], ensure_ascii=True, separators=(",", ":"))


def _vaccine_label(code: str | None, abbreviation: str | None, description: str | None) -> str:
    parts = [part for part in (abbreviation, description, code) if part]
    return " | ".join(parts) if parts else "Imunizante não identificado"


def _statewide(rows: Iterable[dict[str, Any]]) -> bool:
    materialized = tuple(rows)
    for field in ("patient_municipality_code", "application_municipality_code"):
        codes = {row[field] for row in materialized if row.get(field)}
        complete_sp = len(codes) == EXPECTED_SP_MUNICIPALITIES and all(
            code.startswith("35") for code in codes
        )
        if complete_sp:
            return True
    return False


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _source_column(columns: set[str], canonical: str) -> str | None:
    return next((field for field in FIELD_ALIASES[canonical] if field in columns), None)


def _sql_text(columns: set[str], canonical: str) -> str:
    column = _source_column(columns, canonical)
    return f"CAST({_quote(column)} AS VARCHAR)" if column else "CAST(NULL AS VARCHAR)"


def _decode_csv(content: bytes) -> str:
    if not content:
        raise ValueError("O arquivo CSV está vazio.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("O CSV excede o limite de 25 MiB.")
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Encoding não suportado; use UTF-8 ou Windows-1252.")


def _csv_reader(decoded: str) -> csv.DictReader:
    try:
        dialect = csv.Sniffer().sniff(decoded[:8192], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return csv.DictReader(io.StringIO(decoded), dialect=dialect)


def _validate_csv_headers(fieldnames: list[str] | None) -> set[str]:
    if not fieldnames:
        raise ValueError("O CSV não contém cabeçalho.")
    headers = {str(name).strip().lower() for name in fieldnames if name}
    if not any(alias in headers for alias in FIELD_ALIASES["vaccination_date"]):
        raise ValueError("Schema inválido: falta uma coluna de data de vacinação.")
    vaccine_columns = {
        alias
        for key in ("vaccine_code", "vaccine_abbreviation", "vaccine_description")
        for alias in FIELD_ALIASES[key]
    }
    if not headers.intersection(vaccine_columns):
        raise ValueError("Schema inválido: informe código, sigla ou descrição da vacina.")
    return headers


def _accumulate_csv_record(
    record: dict[str, Any], grouped: Counter[tuple[Any, ...]]
) -> bool:
    if not record or not any(_norm(value) for value in record.values()):
        return False
    if None in record:
        raise ValueError("O CSV contém linhas com quantidade de colunas inconsistente.")
    normalized = {str(key).strip().lower(): value for key, value in record.items() if key}
    canonical = _canonical_record(normalized)
    if canonical["date"] is None:
        raise ValueError("O CSV contém datas de vacinação inválidas.")
    if not any(
        canonical[key]
        for key in ("vaccine_code", "vaccine_abbreviation", "vaccine_description")
    ):
        raise ValueError("Há registros sem código, sigla ou descrição da vacina.")
    grouped[_group_key(canonical)] += 1
    return True


def _csv_dimensions(headers: set[str], rows: tuple[dict[str, Any], ...]) -> dict[str, bool]:
    return {
        "sex": bool(headers.intersection(FIELD_ALIASES["sex"]))
        and any(row.get("sex") for row in rows),
        "age": bool(headers.intersection(FIELD_ALIASES["age"] + FIELD_ALIASES["birth_date"]))
        and any(row.get("age_group") for row in rows),
        "vaccine_code": bool(headers.intersection(FIELD_ALIASES["vaccine_code"])),
        "vaccine_abbreviation": bool(headers.intersection(FIELD_ALIASES["vaccine_abbreviation"])),
        "vaccine_description": bool(headers.intersection(FIELD_ALIASES["vaccine_description"])),
        "patient_municipality": bool(
            headers.intersection(FIELD_ALIASES["patient_municipality_code"])
        ),
        "application_municipality": bool(
            headers.intersection(FIELD_ALIASES["application_municipality_code"])
        ),
    }


def _pni_response_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = next(
            (
                payload[key]
                for key in ("doses_aplicadas_pni", "data", "items", "results", "records")
                if isinstance(payload.get(key), list)
            ),
            None,
        )
    else:
        records = None
    if records is None or any(not isinstance(record, dict) for record in records):
        raise ValueError("A API PNI retornou um formato inválido.")
    return records


def _iter_pni_records(
    url: str, limit: int, timeout: int, max_pages: int
) -> Iterator[dict[str, Any]]:
    offset = 0
    for _ in range(max_pages):
        try:
            response = requests.get(
                url,
                params={"limit": limit, "offset": offset},
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"API PNI indisponível ({type(exc).__name__}).") from None
        records = _pni_response_rows(response.json())
        if not records:
            return
        yield from records
        offset += len(records)
        if len(records) < limit:
            return
    raise ValueError("A API PNI excedeu o limite de páginas configurado.")


def _record_in_state(record: dict[str, Any], target_uf: str) -> bool:
    state = _norm(record.get("sigla_uf_paciente"))
    if state:
        return state.upper() == target_uf.upper()
    code = _norm(record.get("codigo_municipio_paciente"))
    return target_uf.upper() != "SP" or not code or code.startswith("35")


def _valid_pni_record(canonical: dict[str, Any], year: int) -> bool:
    applied_on = canonical["date"]
    has_vaccine = any(
        canonical[key] for key in ("vaccine_code", "vaccine_abbreviation", "vaccine_description")
    )
    return applied_on is not None and applied_on.year == year and has_vaccine


def _source_dimensions(columns: set[str]) -> dict[str, bool]:
    return {
        "sex": _source_column(columns, "sex") is not None,
        "age": any(_source_column(columns, key) is not None for key in ("age", "birth_date")),
        "vaccine_code": _source_column(columns, "vaccine_code") is not None,
        "vaccine_abbreviation": _source_column(columns, "vaccine_abbreviation") is not None,
        "vaccine_description": _source_column(columns, "vaccine_description") is not None,
        "patient_municipality": _source_column(columns, "patient_municipality_code") is not None,
        "application_municipality": _source_column(columns, "application_municipality_code")
        is not None,
    }


def _local_sql(path: Path, columns: set[str]) -> str:
    date_column = _source_column(columns, "vaccination_date")
    if date_column is None:
        raise ValueError("A fonte local não contém uma data de vacinação reconhecida.")
    date_text = f"CAST({_quote(date_column)} AS VARCHAR)"
    applied_date = (
        f"COALESCE(TRY_CAST({date_text} AS DATE), "
        f"TRY_STRPTIME({date_text}, '%d/%m/%Y')::DATE, "
        f"TRY_STRPTIME({date_text}, '%Y%m%d')::DATE)"
    )
    birth_column = _source_column(columns, "birth_date")
    age_column = _source_column(columns, "age")
    if birth_column:
        birth_text = f"CAST({_quote(birth_column)} AS VARCHAR)"
        birth_date = (
            f"COALESCE(TRY_CAST({birth_text} AS DATE), "
            f"TRY_STRPTIME({birth_text}, '%d/%m/%Y')::DATE, "
            f"TRY_STRPTIME({birth_text}, '%Y%m%d')::DATE)"
        )
        age_expression = (
            f"DATE_DIFF('year', {birth_date}, {applied_date}) - "
            f"CASE WHEN STRFTIME({applied_date}, '%m-%d') < STRFTIME({birth_date}, '%m-%d') "
            "THEN 1 ELSE 0 END"
        )
    elif age_column:
        age_expression = f"TRY_CAST({_quote(age_column)} AS INTEGER)"
    else:
        age_expression = "CAST(NULL AS INTEGER)"

    escaped_path = path.as_posix().replace("'", "''")
    select_columns = [
        f"YEAR({applied_date})::INTEGER AS year",
        f"MONTH({applied_date})::INTEGER AS month",
        f"{_sql_text(columns, 'vaccine_code')} AS vaccine_code",
        f"{_sql_text(columns, 'vaccine_abbreviation')} AS vaccine_abbreviation",
        f"{_sql_text(columns, 'vaccine_description')} AS vaccine_description",
        f"{_sql_text(columns, 'sex')} AS sex",
        f"{age_expression} AS age_years",
        f"{_sql_text(columns, 'patient_municipality_code')} AS patient_municipality_code",
        f"{_sql_text(columns, 'patient_municipality_name')} AS patient_municipality_name",
        f"{_sql_text(columns, 'application_municipality_code')} AS application_municipality_code",
        f"{_sql_text(columns, 'application_municipality_name')} AS application_municipality_name",
    ]
    return (
        "WITH normalized AS (SELECT "
        + ", ".join(select_columns)
        + f" FROM read_json_auto('{escaped_path}', format='newline_delimited')) "
        "SELECT year, month, vaccine_code, vaccine_abbreviation, vaccine_description, "
        "sex, CASE WHEN age_years BETWEEN 0 AND 4 THEN '0-4' "
        "WHEN age_years BETWEEN 5 AND 59 THEN '5-59' "
        "WHEN age_years BETWEEN 60 AND 120 THEN '60+' ELSE NULL END AS age_group, "
        "patient_municipality_code, patient_municipality_name, "
        "application_municipality_code, application_municipality_name, COUNT(*) AS doses "
        "FROM normalized WHERE year IS NOT NULL "
        "GROUP BY ALL ORDER BY year, month"
    )


@lru_cache(maxsize=2)
def _load_local_cached(path_value: str, modified_ns: int, size: int) -> AnalyticsSnapshot:
    del modified_ns, size
    path = Path(path_value)
    escaped_path = path.as_posix().replace("'", "''")
    con = duckdb.connect(":memory:")
    try:
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_json_auto('{escaped_path}', format='newline_delimited')"
        ).fetchall()
        columns = {row[0] for row in schema}
        result = con.execute(_local_sql(path, columns)).fetchdf()
    finally:
        con.close()
    rows = tuple(result.to_dict(orient="records"))
    total_rows = sum(int(row["doses"]) for row in rows)
    updated = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    return AnalyticsSnapshot(
        rows=rows,
        source="PNI | JSONL local",
        source_updated_at=updated,
        total_rows=total_rows,
        statewide=_statewide(rows),
        dimensions=_source_dimensions(columns),
    )


@lru_cache(maxsize=2)
def _load_demo_cached(path_value: str, modified_ns: int, size: int) -> AnalyticsSnapshot:
    del modified_ns, size
    path = Path(path_value)
    con = duckdb.connect(str(path), read_only=True)
    try:
        cursor = con.execute("SELECT * FROM analytics_groups ORDER BY year, month")
        columns = [column[0] for column in cursor.description]
        rows = tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
        metadata = con.execute("SELECT dimensions FROM analytics_metadata").fetchone()
        if metadata is None:
            raise ValueError("Metadados da base de demonstração ausentes.")
        dimensions = json.loads(metadata[0])
    finally:
        con.close()
    return AnalyticsSnapshot(
        rows=rows,
        source="Demonstração | dados sintéticos",
        source_updated_at=datetime.fromtimestamp(path.stat().st_mtime).astimezone(),
        total_rows=sum(int(row["doses"]) for row in rows),
        statewide=_statewide(rows),
        dimensions=dimensions,
        warnings=("Dados sintéticos de demonstração; não representam indicadores reais.",),
    )


class VaccinationAnalyticsRepository:
    def __init__(self, raw_dir: Path, analytics_db_path: Path | None = None) -> None:
        self.raw_dir = raw_dir
        self.analytics_db_path = analytics_db_path

    def local_snapshot(self) -> AnalyticsSnapshot:
        configured_name = os.getenv("RAW_FILE_NAME", "pni_2024.jsonl")
        path = self.raw_dir / configured_name
        if not path.is_file():
            if self.analytics_db_path is None:
                raise FileNotFoundError("Arquivo local de vacinação não encontrado.")
            demo_path = self.analytics_db_path.resolve()
            if not demo_path.is_file():
                raise FileNotFoundError("Base de demonstração não encontrada.")
            stat = demo_path.stat()
            return _load_demo_cached(str(demo_path), stat.st_mtime_ns, stat.st_size)
        stat = path.stat()
        return _load_local_cached(str(path.resolve()), stat.st_mtime_ns, stat.st_size)

    def csv_snapshot(self, content: bytes) -> AnalyticsSnapshot:
        reader = _csv_reader(_decode_csv(content))
        headers = _validate_csv_headers(reader.fieldnames)
        grouped: Counter[tuple[Any, ...]] = Counter()
        accepted = 0
        for record in reader:
            if _accumulate_csv_record(record, grouped):
                accepted += 1
            if accepted > MAX_UPLOAD_ROWS:
                raise ValueError("O CSV excede o limite de 500.000 linhas.")
        if accepted == 0:
            raise ValueError("O CSV não contém registros.")
        rows = _counter_rows(grouped)
        return AnalyticsSnapshot(
            rows=rows,
            source="CSV carregado (agregado em memória)",
            source_updated_at=datetime.now().astimezone(),
            total_rows=accepted,
            statewide=_statewide(rows),
            dimensions=_csv_dimensions(headers, rows),
        )

    def pni_api_snapshot(self, year: int, target_uf: str = "SP") -> AnalyticsSnapshot:
        base_url = os.getenv("PNI_API_BASE_URL", "https://apidadosabertos.saude.gov.br").rstrip("/")
        endpoint = os.getenv("PNI_API_ENDPOINT", "vacinacao/doses-aplicadas-pni-{year}")
        url = f"{base_url}/{endpoint.format(year=year).lstrip('/')}"
        limit = min(max(int(os.getenv("API_LIMIT", "1000")), 1), 5000)
        timeout = min(max(int(os.getenv("API_TIMEOUT", "30")), 5), 120)
        max_pages = min(max(int(os.getenv("PNI_ANALYTICS_MAX_PAGES", "10000")), 1), 10000)
        grouped: Counter[tuple[Any, ...]] = Counter()
        observed_fields: set[str] = set()
        accepted = 0
        for record in _iter_pni_records(url, limit, timeout, max_pages):
            observed_fields.update(record.keys())
            if not _record_in_state(record, target_uf):
                continue
            canonical = _canonical_record(record)
            if not _valid_pni_record(canonical, year):
                continue
            grouped[_group_key(canonical)] += 1
            accepted += 1

        rows = _counter_rows(grouped)
        if not rows:
            raise ValueError("A API PNI não retornou doses para o período e estado selecionados.")
        return AnalyticsSnapshot(
            rows=rows,
            source="Ministério da Saúde | API PNI",
            source_updated_at=datetime.now().astimezone(),
            total_rows=accepted,
            statewide=_statewide(rows),
            dimensions=_source_dimensions(observed_fields),
        )


def _canonical_record(record: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for canonical, aliases in FIELD_ALIASES.items():
        resolved[canonical] = next(
            (_norm(record.get(alias)) for alias in aliases if _norm(record.get(alias))),
            None,
        )
    applied_on = _date(resolved.get("vaccination_date"))
    age_years = _age_years(resolved, applied_on) if applied_on else None
    return {
        "date": applied_on,
        "vaccine_code": resolved.get("vaccine_code"),
        "vaccine_abbreviation": resolved.get("vaccine_abbreviation"),
        "vaccine_description": resolved.get("vaccine_description"),
        "sex": _normalize_sex(resolved.get("sex")),
        "age_group": _age_group(age_years),
        "patient_municipality_code": resolved.get("patient_municipality_code"),
        "patient_municipality_name": resolved.get("patient_municipality_name"),
        "application_municipality_code": resolved.get("application_municipality_code"),
        "application_municipality_name": resolved.get("application_municipality_name"),
    }


def _normalize_sex(value: Any) -> str | None:
    normalized = _norm(value)
    if normalized is None:
        return None
    key = normalized.casefold()
    labels = {
        "m": "Masculino",
        "masculino": "Masculino",
        "f": "Feminino",
        "feminino": "Feminino",
    }
    return labels.get(key, normalized)


def _group_key(record: dict[str, Any]) -> tuple[Any, ...]:
    applied_on = record["date"]
    return (
        applied_on.year,
        applied_on.month,
        record["vaccine_code"],
        record["vaccine_abbreviation"],
        record["vaccine_description"],
        record["sex"],
        record["age_group"],
        record["patient_municipality_code"],
        record["patient_municipality_name"],
        record["application_municipality_code"],
        record["application_municipality_name"],
    )


def _counter_rows(grouped: Counter[tuple[Any, ...]]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {**dict(zip(GROUP_FIELDS, key, strict=True)), "doses": doses}
        for key, doses in grouped.items()
    )


def csv_snapshot(content: bytes) -> AnalyticsSnapshot:
    return VaccinationAnalyticsRepository(Path()).csv_snapshot(content)


def postgres_snapshot(dsn: str, table: str, year: int) -> AnalyticsSnapshot:
    if not re.fullmatch(r"(?:[A-Za-z_]\w*\.)?[A-Za-z_]\w*", table):
        raise ValueError("VACCINATION_TABLE deve ser um identificador SQL simples.")
    try:
        from psycopg import connect
        from psycopg.conninfo import make_conninfo
    except ImportError as exc:
        raise RuntimeError("Driver PostgreSQL não instalado.") from exc

    quoted_table = ".".join(_quote(part) for part in table.split("."))
    conninfo = make_conninfo(dsn, sslmode="require", connect_timeout=5)
    query = f"""
        WITH source_rows AS (
            SELECT dt_vacina::date AS vaccination_date,
                   co_vacina::text AS vaccine_code,
                   ds_vacina::text AS vaccine_description,
                   tp_sexo_paciente::text AS sex,
                   CASE
                       WHEN dt_nascimento_paciente IS NULL THEN NULL
                       ELSE EXTRACT(
                           YEAR FROM age(dt_vacina::date, dt_nascimento_paciente::date)
                       )::integer
                   END AS age_years,
                   co_municipio_paciente::text AS patient_municipality_code
            FROM {quoted_table}
            WHERE dt_vacina >= %s AND dt_vacina < %s
        )
        SELECT EXTRACT(YEAR FROM vaccination_date)::integer AS year,
               EXTRACT(MONTH FROM vaccination_date)::integer AS month,
               vaccine_code, NULL::text AS vaccine_abbreviation, vaccine_description,
               CASE WHEN lower(sex) IN ('m', 'masculino') THEN 'Masculino'
                    WHEN lower(sex) IN ('f', 'feminino') THEN 'Feminino' ELSE sex END AS sex,
               CASE WHEN age_years BETWEEN 0 AND 4 THEN '0-4'
                    WHEN age_years BETWEEN 5 AND 59 THEN '5-59'
                    WHEN age_years BETWEEN 60 AND 120 THEN '60+' ELSE NULL END AS age_group,
               patient_municipality_code, NULL::text AS patient_municipality_name,
               NULL::text AS application_municipality_code,
               NULL::text AS application_municipality_name,
               COUNT(*)::bigint AS doses
        FROM source_rows
        GROUP BY 1, 2, 3, 5, 6, 7, 8
        ORDER BY 1, 2
    """
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    try:
        with connect(conninfo) as connection, connection.cursor() as cursor:
            cursor.execute(query, (start, end))
            names = [column.name for column in cursor.description]
            rows = tuple(dict(zip(names, row, strict=True)) for row in cursor.fetchall())
    except Exception as exc:
        raise RuntimeError(f"PostgreSQL indisponível ({type(exc).__name__}).") from None

    return AnalyticsSnapshot(
        rows=rows,
        source="PostgreSQL (SSL obrigatório)",
        source_updated_at=datetime.now().astimezone(),
        total_rows=sum(int(row["doses"]) for row in rows),
        statewide=_statewide(rows),
        dimensions={
            "sex": True,
            "age": True,
            "vaccine_code": True,
            "vaccine_abbreviation": False,
            "vaccine_description": True,
            "patient_municipality": True,
            "application_municipality": False,
        },
    )
