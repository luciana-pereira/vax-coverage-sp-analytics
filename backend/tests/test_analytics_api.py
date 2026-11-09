"""Testes focados dos adaptadores agregados e endpoints de analytics."""

from __future__ import annotations

import json
import sys
import types

from app.repositories import vaccination_analytics_repository
from app.repositories.vaccination_analytics_repository import AnalyticsSnapshot, postgres_snapshot
from app.services import vaccination_analytics_service
from app.services.vaccination_analytics_service import VaccinationAnalyticsService


def test_local_pni_endpoint_returns_real_aggregates_without_identifiers(
    settings, make_client, monkeypatch
):
    monkeypatch.setenv("RAW_FILE_NAME", "pni.jsonl")
    monkeypatch.delenv("VACCINATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("AIVEN_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "dt_vacina": "2024-01-12",
            "sg_imunobiologico": "BCG",
            "co_municipio_paciente": "350010",
            "no_municipio_paciente": "Adamantina",
            "codigo_paciente": "patient-private",
            "codigo_documento": "document-private",
            "ref_uuid": "uuid-private",
        },
        {
            "dt_vacina": "2024-01-15",
            "sg_imunobiologico": "BCG",
            "co_municipio_paciente": "350010",
            "no_municipio_paciente": "Adamantina",
        },
    ]
    (settings.raw_dir / "pni.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )

    response = make_client().get("/api/v1/analytics", params={"year": 2024})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["total_doses"] == 2
    assert body["monthly"] == [{"month": "2024-01", "doses": 2}]
    assert body["by_vaccine"] == [
        {
            "key": '[null,"BCG",null]',
            "code": None,
            "abbreviation": "BCG",
            "description": None,
            "label": "BCG",
            "doses": 2,
        }
    ]
    assert body["dimensions"]["sex"] is False
    assert body["dimensions"]["age"] is False
    assert "patient-private" not in response.text
    assert "document-private" not in response.text
    assert "uuid-private" not in response.text


def test_csv_upload_aggregates_sex_age_and_keeps_municipality_roles_separate(client):
    content = (
        "co_vacina;ds_vacina;dt_vacina;dt_nascimento_paciente;tp_sexo_paciente;"
        "co_municipio_paciente;no_municipio_paciente;codigo_municipio_estabelecimento;"
        "nome_municipio_estabelecimento;ref_uuid;cpf\n"
        "code-1;Product description;2024-03-15;2020-03-14;M;350010;Patient city;"
        "350020;Application city;uuid-private;12345678900\n"
        "code-1;Product description;2024-03-15;1960-06-20;F;350020;Other patient city;"
        "350010;Other application city;uuid-private-2;99999999999\n"
    ).encode("utf-8")

    response = client.post(
        "/api/v1/analytics/upload",
        content=content,
        headers={"Content-Type": "text/csv", "X-File-Name": "vaccinations.csv"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_rows"] == body["total_doses"] == 2
    assert body["by_sex"] == [
        {"key": "Feminino", "label": "Feminino", "doses": 1},
        {"key": "Masculino", "label": "Masculino", "doses": 1},
    ]
    assert body["by_age_group"] == [
        {"key": "0-4", "label": "0-4", "doses": 1},
        {"key": "60+", "label": "60+", "doses": 1},
    ]
    assert {item["code"] for item in body["filters"]["patient_municipalities"]} == {
        "350010",
        "350020",
    }
    assert {item["code"] for item in body["filters"]["application_municipalities"]} == {
        "350010",
        "350020",
    }
    assert "uuid-private" not in response.text
    assert "12345678900" not in response.text
    token = body["source_token"]
    filtered = client.get(
        "/api/v1/analytics",
        params={"source_token": token, "vaccine": body["filters"]["vaccines"][0]["key"]},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total_doses"] == 2


def test_csv_upload_rejects_missing_vaccination_date(client):
    response = client.post(
        "/api/v1/analytics/upload",
        content=b"co_vacina\ncode-1\n",
        headers={"Content-Type": "text/csv", "X-File-Name": "bad.csv"},
    )

    assert response.status_code == 422
    assert "data de vacinação" in response.json()["detail"]


def test_csv_upload_rejects_rows_with_extra_columns(client):
    response = client.post(
        "/api/v1/analytics/upload",
        content=b"dt_vacina,sg_imunobiologico\n2024-01-01,BCG,unexpected\n",
        headers={"Content-Type": "text/csv", "X-File-Name": "malformed.csv"},
    )

    assert response.status_code == 422
    assert "colunas inconsistente" in response.json()["detail"]


def test_pni_api_endpoint_maps_rnds_fields_and_discards_identifiers(client, monkeypatch):
    record = {
        "co_vacina": "code-7",
        "ds_vacina": "Descrição oficial",
        "dt_vacina": "2024-06-02",
        "dt_nascimento_paciente": "2020-06-03",
        "tp_sexo_paciente": "F",
        "co_municipio_paciente": "350010",
        "no_municipio_paciente": "Patient city",
        "codigo_municipio_estabelecimento": "350020",
        "nome_municipio_estabelecimento": "Application city",
        "sigla_uf_paciente": "SP",
        "codigo_paciente": "patient-private",
        "codigo_documento": "document-private",
        "ref_uuid": "uuid-private",
    }

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"doses_aplicadas_pni": [record]}

    def fake_get(*args, **kwargs):
        return Response()

    monkeypatch.setattr(vaccination_analytics_repository.requests, "get", fake_get)
    monkeypatch.setenv("API_LIMIT", "10")

    response = client.post("/api/v1/analytics/pni", params={"year": 2024})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "Ministério da Saúde | API PNI"
    assert body["total_doses"] == body["accepted_rows"] == 1
    assert body["by_vaccine"][0]["code"] == "code-7"
    assert body["by_vaccine"][0]["description"] == "Descrição oficial"
    assert body["by_age_group"] == [{"key": "0-4", "label": "0-4", "doses": 1}]
    assert body["filters"]["patient_municipalities"][0]["code"] == "350010"
    assert body["filters"]["application_municipalities"][0]["code"] == "350020"
    assert "patient-private" not in response.text
    assert "document-private" not in response.text
    assert "uuid-private" not in response.text


def test_postgres_adapter_forces_ssl_and_queries_only_aggregates(monkeypatch):
    calls = {}

    class FakeCursor:
        description = [types.SimpleNamespace(name="year"), types.SimpleNamespace(name="month")]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def execute(self, query, params):
            calls["query"] = query
            calls["params"] = params

        def fetchall(self):
            return []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def cursor(self):
            return FakeCursor()

    psycopg = types.ModuleType("psycopg")

    def connect(conninfo):
        calls["conninfo"] = conninfo
        return FakeConnection()

    psycopg.connect = connect
    conninfo_module = types.ModuleType("psycopg.conninfo")

    def make_conninfo(dsn, **options):
        calls["sslmode"] = options["sslmode"]
        return "configured-dsn"

    conninfo_module.make_conninfo = make_conninfo
    psycopg.conninfo = conninfo_module
    monkeypatch.setitem(sys.modules, "psycopg", psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.conninfo", conninfo_module)

    snapshot = postgres_snapshot("dsn-not-logged", "public.vaccination", 2024)

    assert calls["sslmode"] == "require"
    assert "ref_uuid" not in calls["query"]
    assert "COUNT(*)" in calls["query"]
    assert snapshot.source == "PostgreSQL (SSL obrigatório)"


def test_postgres_failure_falls_back_without_repeating_attempts(monkeypatch, settings, request):
    calls = []
    vaccination_analytics_service._postgres_snapshot_cached.cache_clear()
    request.addfinalizer(vaccination_analytics_service._postgres_snapshot_cached.cache_clear)
    monkeypatch.setattr(vaccination_analytics_service, "_POSTGRES_FAILURES", {})
    monkeypatch.setenv("VACCINATION_DATABASE_URL", "dsn-not-logged")
    monkeypatch.setenv("VACCINATION_TABLE", "public.vaccination")

    def fail_connection(*_):
        calls.append(1)
        raise RuntimeError("PostgreSQL indisponível (OperationalError).")

    monkeypatch.setattr(vaccination_analytics_service, "postgres_snapshot", fail_connection)
    local = AnalyticsSnapshot(
        rows=(),
        source="PNI | JSONL local",
        source_updated_at=None,
        total_rows=0,
        statewide=False,
        dimensions={},
    )
    repository = vaccination_analytics_service.VaccinationAnalyticsRepository(settings.raw_dir)
    monkeypatch.setattr(repository, "local_snapshot", lambda: local)
    service = VaccinationAnalyticsService(repository)

    first, first_warnings = service._snapshot(2024)
    second, second_warnings = service._snapshot(2023)

    assert first.source == second.source == "PNI | JSONL local"
    assert first_warnings == second_warnings == ["PostgreSQL indisponível (OperationalError)."]
    assert len(calls) == 1
