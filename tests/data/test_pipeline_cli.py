import json

import pandas as pd
import pytest

from pipeline.cli import cmd_transform, load_pni_jsonl
from pipeline.config import load_settings

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
        "pipeline.extract.ibge.requests.get",
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
        "pipeline.extract.ibge.requests.get",
        lambda *args, **kwargs: pytest.fail(
            "SIDRA total population must not be used as target population"
        ),
    )

    with pytest.raises(RuntimeError, match="população-alvo"):
        cmd_transform(load_settings())


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
        "pipeline.extract.ibge.requests.get",
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
