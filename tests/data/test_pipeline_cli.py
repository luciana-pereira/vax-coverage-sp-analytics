import json

import pandas as pd
import pytest
import requests

from pipeline.cli import cmd_load, cmd_transform, load_pni_jsonl, main, resolve_pni_mapping
from pipeline.config import load_column_mapping, load_settings
from pipeline.transform.transformer import apply_column_mapping

MAPPING = {
    "municipality_code": "code",
    "municipality_name": "name",
    "immunizer": "vaccine",
    "year": "year_value",
    "doses": "dose_count",
}


def _write_source(data_dir):
    rows = [
        {
            "code": "350010",
            "name": "Adamantina",
            "vaccine": "SCR",
            "year_value": 2024,
            "dose_count": 7,
        },
        {
            "code": "350010",
            "name": "Adamantina",
            "vaccine": "INF3",
            "year_value": 2024,
            "dose_count": 5,
        },
    ]
    (data_dir / "raw" / "pni_2024.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    (data_dir / "external" / "column_mapping.json").write_text(
        json.dumps(MAPPING),
        encoding="utf-8",
    )


def test_load_pni_jsonl_normalizes_official_record_fields(tmp_path):
    records = [
        {
            "codigo_documento": "record-sp",
            "codigo_municipio_paciente": "350010",
            "nome_municipio_paciente": "Adamantina",
            "codigo_vacina": "vaccine-code",
            "data_vacina": "2024-01-17 00:00:00-03",
            "sigla_uf_paciente": "SP",
        },
        {
            "codigo_documento": "record-other-state",
            "codigo_municipio_paciente": "411990",
            "nome_municipio_paciente": "Ponta Grossa",
            "codigo_vacina": "vaccine-code",
            "data_vacina": "2024-01-17 00:00:00-03",
            "sigla_uf_paciente": "PR",
        },
    ]
    path = tmp_path / "pni.jsonl"
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    result = load_pni_jsonl(path, target_uf="SP")

    assert result["codigo_documento"].tolist() == ["record-sp"]
    assert result["year"].tolist() == [2024]
    assert result["doses"].tolist() == [1]


def test_load_reduced_pni_jsonl_preserves_real_immunizer_field(tmp_path):
    raw = {
        "co_municipio_paciente": "354330",
        "no_municipio_paciente": "RIBEIRAO PIRES",
        "dt_vacina": "2024-01-23",
        "sg_imunobiologico": "VPC10",
    }
    raw_path = tmp_path / "pni.jsonl"
    raw_path.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    mapping_path = tmp_path / "column_mapping.json"
    mapping_path.write_text(
        json.dumps(
            {
                "municipality_code": "co_municipio_paciente",
                "municipality_name": "no_municipio_paciente",
                "immunizer": "sg_imunobiologico",
            }
        ),
        encoding="utf-8",
    )

    loaded = load_pni_jsonl(raw_path)
    canonical = apply_column_mapping(loaded, load_column_mapping(mapping_path))

    assert canonical.loc[0, "immunizer"] == "VPC10"
    assert canonical.loc[0, "year"] == 2024
    assert canonical.loc[0, "doses"] == 1


def test_rnds_mapping_is_canonical_and_optional_fields_do_not_break_local_raw(tmp_path):
    mapping = {
        "id": "ref_uuid",
        "immunizer": "co_vacina",
        "immunizer_name": "ds_vacina",
        "date": "dt_vacina",
        "birth_date": "dt_nascimento_paciente",
        "sex": "tp_sexo_paciente",
        "municipality_code": "co_municipio_paciente",
        "municipality_name": "no_municipio_paciente",
        "cnes_code": "co_cnes_estabelecimento",
        "facility_name": "no_razao_social_estabelecimento",
    }
    mapping_path = tmp_path / "column_mapping.json"
    mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
    loaded_mapping = load_column_mapping(mapping_path)
    local_raw = pd.DataFrame(
        columns=["co_municipio_paciente", "no_municipio_paciente", "sg_imunobiologico", "dt_vacina"]
    )

    resolved = resolve_pni_mapping(local_raw, loaded_mapping)

    assert resolved["municipality_code"] == "co_municipio_paciente"
    assert resolved["immunizer"] == "sg_imunobiologico"
    assert resolved["date"] == "dt_vacina"
    assert resolved["municipality_name"] == "no_municipio_paciente"
    assert "id" not in resolved
    assert "sex" not in resolved


def test_full_pni_api_schema_uses_confirmed_aliases_without_label_conversion(tmp_path):
    records = [
        {
            "codigo_documento": "record-sp",
            "codigo_municipio_paciente": "350010",
            "nome_municipio_paciente": "Adamantina",
            "codigo_vacina": "vaccine-123",
            "data_vacina": "2024-01-23",
            "sigla_uf_paciente": "SP",
        },
        {
            "codigo_documento": "record-pr",
            "codigo_municipio_paciente": "411990",
            "nome_municipio_paciente": "Ponta Grossa",
            "codigo_vacina": "vaccine-123",
            "data_vacina": "2024-01-23",
            "sigla_uf_paciente": "PR",
        },
    ]
    path = tmp_path / "pni-api.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")
    raw = load_pni_jsonl(path, target_uf="SP")
    mapping = {
        "municipality_code": "co_municipio_paciente",
        "municipality_name": "no_municipio_paciente",
        "immunizer": "sg_imunobiologico",
    }

    canonical = apply_column_mapping(raw, resolve_pni_mapping(raw, mapping))

    assert canonical["municipality_code"].tolist() == ["350010"]
    assert canonical["immunizer"].tolist() == ["vaccine-123"]
    assert canonical["year"].tolist() == [2024]
    assert canonical["doses"].tolist() == [1]


def test_transform_uses_immunizer_target_population_file(data_dir, monkeypatch):
    _write_source(data_dir)
    pd.DataFrame(
        {
            "municipality_code": ["350010", "350010"],
            "year": [2024, 2024],
            "immunizer": ["SCR", "INF3"],
            "population": [10, 20],
        }
    ).to_csv(data_dir / "external" / "target_population.csv", index=False)
    monkeypatch.setattr(
        "pipeline.extract.http.requests.get",
        lambda *args, **kwargs: pytest.fail(
            "SIDRA total population must not replace target population"
        ),
    )

    cmd_transform(load_settings())

    result = pd.read_parquet(data_dir / "processed" / "vaccination.parquet")
    result = result.sort_values("immunizer")
    assert result["population"].tolist() == [20, 10]


def test_transform_fails_when_target_population_file_is_missing(data_dir, monkeypatch):
    _write_source(data_dir)
    monkeypatch.setattr(
        "pipeline.extract.http.requests.get",
        lambda *args, **kwargs: pytest.fail(
            "SIDRA total population must not be used as target population"
        ),
    )

    with pytest.raises(RuntimeError, match="população-alvo"):
        cmd_transform(load_settings())


def test_transform_preserves_previous_parquet_when_write_fails(data_dir, monkeypatch):
    _write_source(data_dir)
    pd.DataFrame(
        {
            "municipality_code": ["350010", "350010"],
            "year": [2024, 2024],
            "immunizer": ["SCR", "INF3"],
            "population": [10, 20],
        }
    ).to_csv(data_dir / "external" / "target_population.csv", index=False)
    settings = load_settings()
    settings.processed_file.parent.mkdir(parents=True, exist_ok=True)
    previous = b"previous-valid-parquet"
    settings.processed_file.write_bytes(previous)

    def fail_write(self, path, index=False):
        from pathlib import Path

        Path(path).write_bytes(b"partial-parquet")
        raise OSError("simulated disk failure")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail_write)

    with pytest.raises(OSError, match="simulated disk failure"):
        cmd_transform(settings)

    assert settings.processed_file.read_bytes() == previous
    assert not list(settings.processed_file.parent.glob(".*.tmp.parquet"))


def test_csv_ingestion_uses_immunizer_target_population_file(data_dir, monkeypatch):
    pd.DataFrame(
        {
            "municipality_code": ["350010", "350010"],
            "year": [2024, 2024],
            "immunizer": ["SCR", "INF3"],
            "population": [10, 20],
        }
    ).to_csv(data_dir / "external" / "target_population.csv", index=False)
    monkeypatch.setattr(
        "pipeline.extract.http.requests.get",
        lambda *args, **kwargs: pytest.fail("CSV ingestion must use target population"),
    )

    from pipeline.ingestion.processor import _attach_population

    vaccination = pd.DataFrame(
        {
            "municipality_code": ["350010", "350010"],
            "municipality_name": ["Adamantina", "Adamantina"],
            "immunizer": ["SCR", "INF3"],
            "year": [2024, 2024],
            "doses": [7, 5],
        }
    )

    result = _attach_population(vaccination).sort_values("immunizer")

    assert result["population"].tolist() == [20, 10]


def test_csv_ingestion_fails_when_an_immunizer_target_is_missing(data_dir):
    pd.DataFrame(
        {
            "municipality_code": ["350010"],
            "year": [2024],
            "immunizer": ["SCR"],
            "population": [10],
        }
    ).to_csv(data_dir / "external" / "target_population.csv", index=False)
    vaccination = pd.DataFrame(
        {
            "municipality_code": ["350010", "350010"],
            "municipality_name": ["Adamantina", "Adamantina"],
            "immunizer": ["SCR", "INF3"],
            "year": [2024, 2024],
            "doses": [7, 5],
        }
    )

    from pipeline.ingestion.processor import _attach_population

    with pytest.raises(RuntimeError, match="sem população-alvo"):
        _attach_population(vaccination)


def test_extract_timeout_reports_stage_without_traceback(data_dir, monkeypatch, caplog):
    settings = load_settings()
    monkeypatch.setattr("pipeline.cli.load_settings", lambda: settings)

    def fail_request(*args, **kwargs):
        raise requests.Timeout("fonte indisponível")

    monkeypatch.setattr("pipeline.extract.http.requests.get", fail_request)
    monkeypatch.setattr("pipeline.extract.http.time.sleep", lambda _: None)

    result = main(["extract", "--year", "2024"])

    assert result == 1
    assert "extract" in caplog.text.lower()
    assert "traceback" not in caplog.text.lower()
    assert not settings.raw_file.exists()


def test_load_refuses_invalid_parquet_before_touching_duckdb(data_dir):
    settings = load_settings()
    pd.DataFrame(
        {
            "municipality_code": ["350010"],
            "year": [2024],
            "doses": [1],
            "population": [10],
        }
    ).to_parquet(settings.processed_file, index=False)

    with pytest.raises(RuntimeError, match="immunizer"):
        cmd_load(settings)

    assert not settings.duckdb_path.exists()
