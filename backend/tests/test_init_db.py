from __future__ import annotations

import json
from dataclasses import replace

import duckdb
import pytest

from app.core.config import ROOT, build_settings, get_settings
from backend.scripts.init_db import init_db


@pytest.fixture
def clean_sources(monkeypatch):
    for name in ("VACCINATION_DATABASE_URL", "AIVEN_DATABASE_URL", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("file_type", ["csv", "parquet"])
def test_init_db_and_analytics_demo(tmp_path, settings, make_client, clean_sources, file_type):
    source = tmp_path / "input.csv"
    source.write_text(
        "dt_vacina,sg_imunobiologico,cpf\n"
        "2024-01-15,DEMO,private-id\n2024-01-16,DEMO,other-id\n",
        encoding="utf-8",
    )
    if file_type == "parquet":
        parquet = tmp_path / "input.parquet"
        with duckdb.connect() as connection:
            connection.execute(
                "CREATE TABLE input AS SELECT * FROM read_csv_auto(?)", [str(source)]
            )
            connection.execute("COPY input TO ? (FORMAT PARQUET)", [str(parquet)])
        source = parquet
    destination = tmp_path / "demo.duckdb"
    init_db(source, destination)
    with duckdb.connect(str(destination), read_only=True) as connection:
        columns = [
            row[1] for row in connection.execute("PRAGMA table_info('analytics_groups')").fetchall()
        ]
        assert "cpf" not in columns
        assert connection.execute("SELECT SUM(doses) FROM analytics_groups").fetchone()[0] == 2
    demo_settings = replace(settings, analytics_db_path=destination)
    client = make_client()
    client.app.dependency_overrides[get_settings] = lambda: demo_settings
    response = client.get("/api/v1/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_doses"] == 2
    assert data["source"] == "Demonstração | dados sintéticos"
    assert any("sintéticos" in warning for warning in data["warnings"])
    assert "private-id" not in response.text


def test_init_db_does_not_replace_existing_destination(tmp_path):
    source = tmp_path / "data.csv"
    source.write_text("dt_vacina,sg_imunobiologico\n2024-01-01,DEMO\n", encoding="utf-8")
    destination = tmp_path / "existing.duckdb"
    destination.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        init_db(source, destination)
    assert destination.read_bytes() == b"keep"


def test_init_db_rejects_bad_schema_without_creating_db(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("name\nexample\n", encoding="utf-8")
    destination = tmp_path / "demo.duckdb"
    with pytest.raises(ValueError, match="data de vacinação"):
        init_db(source, destination)
    assert not destination.exists()


def test_missing_analytics_source_returns_friendly_404(settings, make_client, clean_sources):
    response = make_client().get("/api/v1/analytics")
    assert response.status_code == 404
    assert response.json()["detail"] == "A base de dados ainda não foi carregada ou inicializada."
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.json()["request_id"]


def test_missing_configured_db_returns_friendly_404(settings, make_client, clean_sources, tmp_path):
    client = make_client()
    client.app.dependency_overrides[get_settings] = lambda: replace(
        settings, analytics_db_path=tmp_path / "missing.duckdb"
    )
    response = client.get("/api/v1/analytics")
    assert response.status_code == 404
    assert response.json()["detail"] == "A base de dados ainda não foi carregada ou inicializada."
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.json()["request_id"]
    assert "missing.duckdb" not in response.text


def test_real_jsonl_takes_precedence_over_demo(
    tmp_path, settings, make_client, clean_sources, monkeypatch
):
    source = tmp_path / "demo.csv"
    source.write_text("dt_vacina,sg_imunobiologico\n2024-01-01,DEMO\n", encoding="utf-8")
    destination = tmp_path / "demo.duckdb"
    init_db(source, destination)
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    (settings.raw_dir / "pni.jsonl").write_text(
        json.dumps({"dt_vacina": "2024-02-01", "sg_imunobiologico": "REAL"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAW_FILE_NAME", "pni.jsonl")
    client = make_client()
    client.app.dependency_overrides[get_settings] = lambda: replace(
        settings, analytics_db_path=destination
    )
    response = client.get("/api/v1/analytics")
    assert response.status_code == 200
    assert response.json()["source"] == "PNI | JSONL local"
    assert response.json()["by_vaccine"][0]["abbreviation"] == "REAL"


def test_analytics_db_path_is_absolute_from_repository_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANALYTICS_DB_PATH", "backend/data/demo/vax.duckdb")
    assert build_settings().analytics_db_path == (ROOT / "backend/data/demo/vax.duckdb").resolve()
