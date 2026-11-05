"""Integração dados -> features -> modelo -> API (em diretório temporário)."""

from __future__ import annotations

import pytest

from ml import cli as ml_cli
from ml.config import load_settings


@pytest.fixture
def pipeline_outputs(data_dir, processed_frame):
    settings = load_settings()
    processed_frame.to_parquet(settings.processed_file, index=False)
    ml_cli.cmd_features(settings)
    ml_cli.cmd_train(settings)
    return settings


def test_coverage_endpoint_matches_pandas(pipeline_outputs, api_client):
    import pandas as pd

    features = pd.read_parquet(pipeline_outputs.features_path)
    summary = api_client.get("/api/v1/coverage").json()["summary"]
    assert summary["records"] == len(features)
    assert summary["mean_coverage"] == pytest.approx(features["coverage"].mean(), abs=1e-3)
    assert summary["municipalities"] == features["municipality_code"].nunique()


def test_history_covers_every_year(pipeline_outputs, api_client):
    points = api_client.get("/api/v1/coverage/history").json()["series"][0]["points"]
    assert [p["year"] for p in points] == [2019, 2020, 2021, 2022, 2023]


def test_predictions_use_trained_model(pipeline_outputs, api_client):
    body = api_client.get("/api/v1/predictions", params={"limit": 1000}).json()
    assert body["status"] == "ok"
    assert body["source_year"] == 2023 and body["target_year"] == 2024
    assert body["total"] == 24 * 2 == len(body["items"])
    assert sum(body["class_distribution"].values()) == body["total"]
    for item in body["items"]:
        assert item["predicted_class"] in {"baixo", "moderado", "alto"}
        assert sum(item["probabilities"].values()) == pytest.approx(1.0)

    one = api_client.get(
        "/api/v1/predictions", params={"municipality_code": "3500001", "immunizer": "VAC_A"}
    ).json()
    assert one["total"] == 1 and one["items"][0]["municipality_code"] == "3500001"

    filtered = api_client.get(
        "/api/v1/predictions", params={"predicted_class": body["items"][0]["predicted_class"]}
    ).json()
    assert 0 < filtered["total"] <= body["total"]


def test_models_endpoint_reflects_training_report(pipeline_outputs, api_client):
    import json

    saved = json.loads(pipeline_outputs.metrics_path.read_text(encoding="utf-8"))
    body = api_client.get("/api/v1/models").json()
    assert body["status"] == "ok" and body["best_model"] == saved["best_model"]
    assert {m["name"] for m in body["models"]} == set(saved["models"])
    assert body["split"]["test_year"] == saved["split"]["test_year"]
    assert body["baseline"] is not None


def test_data_quality_sees_all_artifacts(pipeline_outputs, api_client):
    body = api_client.get("/api/v1/data-quality").json()
    present = {a["name"] for a in body["artifacts"] if a["exists"]}
    assert {"features", "ml_dataset", "model", "metrics"} <= present
    assert body["dataset"]["missing_columns"] == []
