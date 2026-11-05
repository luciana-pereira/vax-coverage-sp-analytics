import json

import pandas as pd
import pytest


@pytest.mark.usefixtures("features_file")
class TestWithFeatures:
    def test_coverage_overall(self, client):
        body = client.get("/api/v1/coverage").json()
        summary = body["summary"]
        assert body["status"] == "ok"
        assert summary["records"] == 5 and summary["municipalities"] == 3
        assert summary["mean_coverage"] == pytest.approx(79.2)
        assert summary["mean_deficit"] == pytest.approx(16.0)
        assert summary["municipalities_below_target"] == 3
        assert summary["critical_municipalities"] == 2

    def test_coverage_filtered_by_year(self, client):
        summary = client.get("/api/v1/coverage", params={"year": 2023}).json()["summary"]
        assert summary["records"] == 3
        assert summary["mean_coverage"] == pytest.approx(78.6667, abs=1e-3)
        assert summary["municipalities_below_target"] == 2
        assert summary["critical_municipalities"] == 1

    def test_distribution_ordered_and_ranking(self, client):
        body = client.get("/api/v1/coverage", params={"ranking_limit": 2}).json()
        assert [d["deficit_class"] for d in body["deficit_distribution"]] == [
            "baixo",
            "moderado",
            "alto",
        ]
        assert [d["count"] for d in body["deficit_distribution"]] == [2, 1, 2]
        ranking = body["top_deficit_municipalities"]
        assert [r["municipality_code"] for r in ranking] == ["3300", "2200"]
        assert ranking[1]["mean_deficit"] == pytest.approx(12.5)

    def test_filter_by_immunizer_and_unknown_values(self, client):
        only_y = client.get("/api/v1/coverage", params={"immunizer": "Y"}).json()["summary"]
        assert only_y["records"] == 1
        none = client.get("/api/v1/coverage", params={"immunizer": "Z"}).json()["summary"]
        assert none["records"] == 0 and none["mean_coverage"] is None

    def test_filter_options(self, client):
        body = client.get("/api/v1/coverage/filters").json()
        assert body["years"] == [2022, 2023]
        assert body["immunizers"] == ["X", "Y"]
        assert body["deficit_classes"] == ["baixo", "moderado", "alto"]

    def test_history_aggregated_and_per_municipality(self, client):
        overall = client.get("/api/v1/coverage/history").json()["series"]
        assert [s["key"] for s in overall] == ["all"]
        points = overall[0]["points"]
        assert [p["year"] for p in points] == [2022, 2023]
        assert points[0]["mean_coverage"] == pytest.approx(80.0)

        compare = client.get(
            "/api/v1/coverage/history", params={"municipality_code": ["1100", "2200"]}
        ).json()["series"]
        assert [s["key"] for s in compare] == ["1100", "2200"]
        assert [p["mean_coverage"] for p in compare[1]["points"]] == [70.0, 96.0]

    def test_municipality_list_and_pagination(self, client):
        body = client.get("/api/v1/municipalities", params={"limit": 2}).json()
        assert body["total"] == 3 and len(body["items"]) == 2
        assert [i["municipality_name"] for i in body["items"]] == ["Alpha", "Beta"]
        beta = body["items"][1]
        assert beta["mean_coverage"] == pytest.approx(83.0)
        assert beta["deficit_class"] == "moderado"
        page2 = client.get("/api/v1/municipalities", params={"limit": 2, "offset": 2}).json()
        assert [i["municipality_code"] for i in page2["items"]] == ["3300"]

    def test_municipality_detail(self, client):
        body = client.get("/api/v1/municipalities/2200").json()
        assert body["municipality"]["municipality_name"] == "Beta"
        assert [p["year"] for p in body["history"]] == [2022, 2023]
        assert body["by_immunizer"] == [
            {"immunizer": "X", "mean_coverage": 83.0, "mean_deficit": 12.5}
        ]

    def test_unknown_municipality_is_404(self, client):
        assert client.get("/api/v1/municipalities/9999").status_code == 404

    def test_invalid_parameters_are_422(self, client):
        assert client.get("/api/v1/coverage", params={"year": "abc"}).status_code == 422
        assert client.get("/api/v1/municipalities", params={"limit": 0}).status_code == 422

    def test_data_quality_with_dataset(self, client):
        body = client.get("/api/v1/data-quality").json()
        dataset = body["dataset"]
        assert body["status"] == "ok"
        assert dataset["rows"] == 5 and dataset["duplicate_rows"] == 0
        assert dataset["municipalities"] == 3
        assert (dataset["year_min"], dataset["year_max"]) == (2022, 2023)
        assert dataset["missing_columns"] == []
        assert all(c["null_count"] == 0 for c in dataset["columns"])
        features = next(a for a in body["artifacts"] if a["name"] == "features")
        assert features["exists"] and features["size_bytes"] > 0


def test_models_report_is_served_from_metrics_json(client, settings):
    metrics = {
        "generated_at": "2024-01-01T00:00:00+00:00",
        "target": "deficit_class_next",
        "features": ["coverage"],
        "classes": ["baixo", "alto"],
        "split": {
            "scheme": "temporal",
            "train_years": [2020],
            "validation_year": None,
            "test_year": 2021,
            "n_train": 4,
            "n_validation": 0,
            "n_test": 2,
        },
        "selection": {"criterion": "f1_macro", "split": "test", "note": "n"},
        "best_model": "random_forest",
        "models": {
            "random_forest": {
                "validation": None,
                "test": {
                    "accuracy": 0.5,
                    "precision_macro": 0.5,
                    "precision_weighted": 0.5,
                    "recall_macro": 0.5,
                    "recall_weighted": 0.5,
                    "f1_macro": 0.5,
                    "f1_weighted": 0.5,
                    "confusion_matrix": [[1, 0], [1, 0]],
                },
            }
        },
        "baseline": None,
        "feature_importance": [{"feature": "num__coverage", "importance": 1.0}],
    }
    settings.metrics_path.parent.mkdir(parents=True, exist_ok=True)
    settings.metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    body = client.get("/api/v1/models").json()
    assert body["status"] == "ok" and body["best_model"] == "random_forest"
    assert body["models"][0]["is_best"] is True
    assert body["models"][0]["test"]["confusion_matrix"] == [[1, 0], [1, 0]]
    assert body["feature_importance"][0]["feature"] == "num__coverage"


def test_geo_serves_configured_geojson(settings, make_client, monkeypatch):
    settings.geojson_path.parent.mkdir(parents=True, exist_ok=True)
    settings.geojson_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8"
    )
    body = make_client().get("/api/v1/geo/municipalities").json()
    assert body["status"] == "ok" and body["feature_count"] == 0
    assert body["code_property"] is None and "GEOJSON_CODE_PROPERTY" in body["message"]


def test_geo_rejects_invalid_geojson(settings, make_client):
    settings.geojson_path.parent.mkdir(parents=True, exist_ok=True)
    settings.geojson_path.write_text("[]", encoding="utf-8")
    assert make_client().get("/api/v1/geo/municipalities").json()["status"] == "data_unavailable"


def test_coverage_without_immunizer_dimension_is_unavailable(settings, make_client):
    settings.features_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "municipality_code": ["350010"],
            "year": [2024],
            "coverage": [2.0],
            "deficit": [93.0],
            "deficit_class": ["alto"],
        }
    ).to_parquet(settings.features_path, index=False)

    body = make_client().get("/api/v1/coverage").json()

    assert body["status"] == "data_unavailable"
    assert body["summary"] is None
    assert "immunizer" in body["message"]

    quality = make_client().get("/api/v1/data-quality").json()
    assert quality["status"] == "data_unavailable"
    assert "immunizer" in quality["dataset"]["missing_columns"]
