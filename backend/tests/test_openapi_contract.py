"""Contrato OpenAPI: caminhos, schemas e documentação mínima dos endpoints."""

EXPECTED_PATHS = {
    "/api/v1/health",
    "/api/v1/coverage",
    "/api/v1/coverage/filters",
    "/api/v1/coverage/history",
    "/api/v1/municipalities",
    "/api/v1/municipalities/{municipality_id}",
    "/api/v1/predictions",
    "/api/v1/models",
    "/api/v1/data-quality",
    "/api/v1/geo/municipalities",
}

EXPECTED_SCHEMAS = {
    "HealthResponse",
    "CoverageResponse",
    "CoverageHistoryResponse",
    "MunicipalityListResponse",
    "MunicipalityDetailResponse",
    "PredictionResponse",
    "ModelResponse",
    "DataQualityResponse",
    "GeoResponse",
}


def _spec(client):
    return client.get("/openapi.json").json()


def test_openapi_exposes_exactly_the_documented_paths(client):
    assert set(_spec(client)["paths"]) == EXPECTED_PATHS


def test_openapi_contains_response_schemas(client):
    assert EXPECTED_SCHEMAS <= set(_spec(client)["components"]["schemas"])


def test_every_operation_is_documented_and_get_only(client):
    for path, operations in _spec(client)["paths"].items():
        assert set(operations) == {"get"}, path
        operation = operations["get"]
        assert operation["summary"] and operation["description"], path
        assert "200" in operation["responses"], path


def test_municipality_detail_documents_404(client):
    operation = _spec(client)["paths"]["/api/v1/municipalities/{municipality_id}"]["get"]
    assert "404" in operation["responses"]
    assert "422" in operation["responses"]
