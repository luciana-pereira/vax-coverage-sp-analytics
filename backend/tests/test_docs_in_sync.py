def test_published_api_docs_match_the_live_contract(client):
    """docs/api/openapi.json deve refletir a API real (regenere com scripts/export_openapi.py)."""
    import json
    from pathlib import Path

    published = json.loads(
        (Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json").read_text(
            encoding="utf-8"
        )
    )
    assert published == client.get("/openapi.json").json()
