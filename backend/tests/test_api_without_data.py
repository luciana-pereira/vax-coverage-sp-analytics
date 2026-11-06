"""Sem artefatos, a API deve sinalizar a lacuna e nunca fabricar valores."""

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import create_app


def test_coverage_without_data(client):
    body = client.get("/api/v1/coverage").json()
    assert body["status"] == "data_unavailable"
    assert body["summary"] is None and body["top_deficit_municipalities"] == []
    assert "features" in body["message"].lower()


def test_history_filters_and_municipalities_without_data(client):
    assert client.get("/api/v1/coverage/history").json()["status"] == "data_unavailable"
    assert client.get("/api/v1/coverage/filters").json()["years"] == []
    by_immunizer = client.get("/api/v1/coverage/immunizers").json()
    assert by_immunizer["status"] == "data_unavailable" and by_immunizer["items"] == []
    listing = client.get("/api/v1/municipalities").json()
    assert listing["status"] == "data_unavailable" and listing["items"] == []


def test_municipality_detail_without_data_is_404(client):
    response = client.get("/api/v1/municipalities/1100")
    assert response.status_code == 404
    assert "detail" in response.json()


def test_predictions_without_model(client):
    body = client.get("/api/v1/predictions").json()
    assert body["status"] == "model_unavailable" and body["items"] == []


def test_models_without_training(client):
    body = client.get("/api/v1/models").json()
    assert body["status"] == "not_trained" and body["models"] == []


def test_data_quality_lists_gaps_without_data(client):
    body = client.get("/api/v1/data-quality").json()
    assert body["status"] == "data_unavailable" and body["dataset"] is None
    assert any("GeoJSON" in gap for gap in body["known_gaps"])
    assert any("População-alvo" in gap for gap in body["known_gaps"])
    assert {a["name"] for a in body["artifacts"]} >= {"raw", "features", "model", "geojson"}
    assert not any(a["exists"] for a in body["artifacts"])


def test_geo_without_geojson(client):
    body = client.get("/api/v1/geo/municipalities").json()
    assert body["status"] == "data_unavailable" and body["geojson"] is None


def test_http_errors_include_request_id_and_safe_client_detail():
    app = create_app()

    @app.get("/test/conflict")
    def conflict():
        raise HTTPException(status_code=409, detail="A ingestão já foi registrada.")

    response = TestClient(app, raise_server_exceptions=False).get("/test/conflict")

    assert response.status_code == 409
    assert response.json()["detail"] == "A ingestão já foi registrada."
    assert response.headers["x-request-id"] == response.json()["request_id"]


def test_validation_errors_use_a_safe_standard_response():
    app = create_app()

    @app.get("/test/validation")
    def validation(year: int):
        return {"year": year}

    response = TestClient(app, raise_server_exceptions=False).get(
        "/test/validation?year=not-a-year"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Parâmetros ou dados inválidos."
    assert response.headers["x-request-id"] == response.json()["request_id"]


def test_unexpected_errors_are_sanitized_and_logged(caplog):
    app = create_app()

    @app.get("/test/failure")
    def failure():
        raise RuntimeError("C:\\private\\source.py:42")

    response = TestClient(app, raise_server_exceptions=False).get("/test/failure")
    body = response.json()

    assert response.status_code == 500
    assert body["detail"] == "Erro interno do serviço. Tente novamente mais tarde."
    assert "private" not in response.text
    assert response.headers["x-request-id"] == body["request_id"]
    assert body["request_id"] in caplog.text
