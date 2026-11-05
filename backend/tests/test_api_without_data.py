"""Sem artefatos, a API deve sinalizar a lacuna e nunca fabricar valores."""


def test_coverage_without_data(client):
    body = client.get("/api/v1/coverage").json()
    assert body["status"] == "data_unavailable"
    assert body["summary"] is None and body["top_deficit_municipalities"] == []
    assert "features" in body["message"].lower()


def test_history_filters_and_municipalities_without_data(client):
    assert client.get("/api/v1/coverage/history").json()["status"] == "data_unavailable"
    assert client.get("/api/v1/coverage/filters").json()["years"] == []
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
