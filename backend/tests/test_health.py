from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app.core.config import build_settings


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert {"app", "version", "environment"} <= set(body)


def test_docs_redoc_and_openapi_are_served(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_cors_allows_dev_frontend(client):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:4200"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"


def test_cors_allows_configured_origin_and_csv_upload_preflight(settings, monkeypatch):
    origin = "https://vax-coverage.vercel.app"
    monkeypatch.setattr(app_main, "get_settings", lambda: replace(settings, cors_origins=[origin]))
    client = TestClient(app_main.create_app())

    response = client.options(
        "/api/v1/analytics/upload",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-file-name",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]

    upload = client.post(
        "/api/v1/analytics/upload",
        headers={"Origin": origin, "Content-Type": "text/csv", "X-File-Name": "empty.csv"},
        content=b"",
    )
    assert upload.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def test_cors_preflight_reads_environment_origin(monkeypatch, method):
    origin = "https://vax-coverage.vercel.app"
    monkeypatch.setenv("CORS_ORIGINS", f"http://localhost:4200, {origin}")
    monkeypatch.setattr(app_main, "get_settings", build_settings)
    client = TestClient(app_main.create_app())

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert method in response.headers["access-control-allow-methods"].split(", ")


def test_cors_preflight_rejects_unconfigured_origin(settings, monkeypatch):
    monkeypatch.setattr(
        app_main,
        "get_settings",
        lambda: replace(settings, cors_origins=["https://vax-coverage.vercel.app"]),
    )
    client = TestClient(app_main.create_app())
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://other.example",
            "Access-Control-Request-Method": "PUT",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("https://project-preview.vercel.app", True),
        ("https://vercel.app", False),
        ("http://project.vercel.app", False),
        ("https://project.vercel.app.attacker.example", False),
        ("https://project.evil-vercel.app", False),
        ("https://project.sub.vercel.app", False),
    ],
)
def test_vercel_wildcard_is_explicit_and_constrained(settings, monkeypatch, origin, allowed):
    monkeypatch.setattr(
        app_main,
        "get_settings",
        lambda: replace(settings, cors_origins=["https://*.vercel.app"]),
    )
    client = TestClient(app_main.create_app())
    response = client.get("/api/v1/health", headers={"Origin": origin})
    assert ("access-control-allow-origin" in response.headers) is allowed
    if allowed:
        assert response.headers["access-control-allow-origin"] == origin


def test_vercel_preview_not_allowed_by_default(client):
    response = client.get(
        "/api/v1/health", headers={"Origin": "https://project-preview.vercel.app"}
    )
    assert "access-control-allow-origin" not in response.headers
