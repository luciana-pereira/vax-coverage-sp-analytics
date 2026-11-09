"""E2E: fonte local -> CLIs do pipeline e de ML -> API.

A fonte é um JSONL sintético gerado em diretório temporário, com nomes de
colunas arbitrários e mapeamento declarado em `column_mapping.json`. Não
representa o schema real da API do Ministério da Saúde.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]

MAPPING = {
    "municipality_code": "cod_mun",
    "municipality_name": "nome_mun",
    "immunizer": "vacina",
    "year": "ano",
    "doses": "qtd",
    "population": "populacao",
}


def _configurable_env_names() -> list[str]:
    """Variáveis documentadas em .env.example (um .env local não pode vazar para o teste)."""
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    return re.findall(r"^([A-Z][A-Z0-9_]*)=", text, flags=re.MULTILINE)


def _run(module: str, command: str, data_dir: Path) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "DATA_DIR": str(data_dir),
        "PYTHONPATH": str(ROOT),
        "DEDUPLICATE_RAW": "false",
    }
    for name in _configurable_env_names():
        env.pop(name, None)
    env["DATA_DIR"] = str(data_dir)
    env["RAW_FILE_NAME"] = "pni_2024.jsonl"
    env["DEDUPLICATE_RAW"] = "false"
    return subprocess.run(
        [sys.executable, "-m", module, command],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )


@pytest.fixture
def source_files(data_dir, processed_frame):
    """Registros brutos (doses divididas em duas linhas) + população-alvo externa."""
    lines = []
    for row in processed_frame.itertuples():
        lines.append(
            {
                "cod_mun": row.municipality_code,
                "nome_mun": row.municipality_name,
                "vacina": row.immunizer,
                "ano": row.year,
                "qtd": row.doses,
                "populacao": row.population,
            }
        )
    (data_dir / "raw" / "pni_2024.jsonl").write_text(
        "\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8"
    )
    mapping_path = data_dir / "external" / "column_mapping.json"
    mapping_path.write_text(json.dumps(MAPPING), encoding="utf-8")
    processed_frame[
        ["municipality_code", "year", "immunizer", "population"]
    ].drop_duplicates().to_csv(data_dir / "external" / "target_population.csv", index=False)
    (data_dir / "external" / "coverage_targets.json").write_text(
        json.dumps({"VAC_A": 95, "VAC_B": 95}),
        encoding="utf-8",
    )
    return data_dir


def test_full_flow_from_raw_to_api(source_files, processed_frame, api_client):
    for module, command in [
        ("pipeline.cli", "transform"),
        ("pipeline.cli", "validate"),
        ("pipeline.cli", "load"),
        ("ml.cli", "features"),
        ("ml.cli", "train"),
        ("ml.cli", "evaluate"),
        ("ml.cli", "predict"),
    ]:
        result = _run(module, command, source_files)
        assert result.returncode == 0, f"{module} {command}: {result.stderr[-800:]}"

    processed = pd.read_parquet(source_files / "processed" / "vaccination.parquet")
    assert processed["doses"].sum() == processed_frame["doses"].sum()
    assert (source_files / "processed" / "vax.duckdb").exists()

    coverage = api_client.get("/api/v1/coverage").json()
    assert coverage["status"] == "ok"
    assert coverage["summary"]["municipalities"] == processed_frame["municipality_code"].nunique()

    predictions = api_client.get("/api/v1/predictions").json()
    assert predictions["status"] == "ok" and predictions["total"] > 0
    assert api_client.get("/api/v1/models").json()["status"] == "ok"
    assert api_client.get("/api/v1/data-quality").json()["status"] == "ok"


def test_transform_without_mapping_fails_with_clear_message(data_dir):
    (data_dir / "raw" / "pni_2024.jsonl").write_text('{"a": 1}\n', encoding="utf-8")
    result = _run("pipeline.cli", "transform", data_dir)
    assert result.returncode == 1
    assert "Mapeamento de colunas ausente" in result.stderr


def test_transform_without_raw_data_fails(data_dir):
    result = _run("pipeline.cli", "transform", data_dir)
    assert result.returncode == 1 and "Dados brutos ausentes" in result.stderr


def test_train_without_features_fails(data_dir):
    result = _run("ml.cli", "train", data_dir)
    assert result.returncode == 1 and "features" in result.stderr
