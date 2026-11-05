import json

import joblib
import pandas as pd
import pytest

from ml.features.build_features import (
    DEFICIT_LABELS,
    TARGET_COLUMN,
    build_ml_dataset,
    build_vaccination_features,
    feature_columns,
)
from ml.inference.predict import load_feature_list, predict, predict_with_probabilities
from ml.models.registry import MODEL_NAMES
from ml.training.train import train_models


@pytest.fixture
def dataset(processed_frame):
    features = build_vaccination_features(processed_frame, "doses", "population", "year")
    return build_ml_dataset(features)


@pytest.fixture
def trained(dataset, tmp_path):
    model_path = tmp_path / "model.joblib"
    metrics_path = tmp_path / "metrics.json"
    report = train_models(
        dataset,
        features=feature_columns(dataset),
        target=TARGET_COLUMN,
        year_col="year",
        model_path=model_path,
        metrics_path=metrics_path,
        class_order=DEFICIT_LABELS,
        baseline_col="deficit_class",
    )
    return report, model_path, metrics_path, dataset


def test_training_compares_all_candidates_with_temporal_split(trained):
    report, model_path, metrics_path, _ = trained
    assert set(report["models"]) == set(MODEL_NAMES)
    split = report["split"]
    assert split["train_years"] == [2019, 2020]
    assert split["validation_year"] == 2021
    assert split["test_year"] == 2022
    assert max(split["train_years"]) < split["validation_year"] < split["test_year"]
    assert report["selection"]["split"] == "validation"
    assert model_path.exists() and metrics_path.exists()


def test_metrics_are_complete_and_consistent(trained):
    report, _, metrics_path, _ = trained
    saved = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert saved["best_model"] == report["best_model"]
    best_score = report["models"][report["best_model"]]["validation"]["f1_macro"]
    assert all(e["validation"]["f1_macro"] <= best_score for e in report["models"].values())
    test = report["models"][report["best_model"]]["test"]
    for key in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted"):
        assert 0.0 <= test[key] <= 1.0
    matrix = test["confusion_matrix"]
    assert len(matrix) == len(report["classes"])
    assert sum(map(sum, matrix)) == report["split"]["n_test"]


def test_no_target_leakage_in_features(trained):
    report, *_ = trained
    assert "deficit_class" not in report["features"]
    assert TARGET_COLUMN not in report["features"]


def test_baseline_and_feature_importance_are_reported(trained):
    report, *_ = trained
    assert report["baseline"]["test"]["f1_macro"] >= 0.0
    assert report["feature_importance"]


def test_training_requires_two_periods(dataset, tmp_path):
    single = dataset[dataset["year"] == 2019]
    with pytest.raises(ValueError):
        train_models(
            single,
            features=feature_columns(dataset),
            target=TARGET_COLUMN,
            year_col="year",
            model_path=tmp_path / "m.joblib",
            metrics_path=tmp_path / "m.json",
        )


def test_two_periods_flags_selection_on_test(dataset, tmp_path):
    two = dataset[dataset["year"].isin([2019, 2020])]
    report = train_models(
        two,
        features=feature_columns(dataset),
        target=TARGET_COLUMN,
        year_col="year",
        model_path=tmp_path / "m.joblib",
        metrics_path=tmp_path / "m.json",
    )
    assert report["selection"]["split"] == "test" and report["selection"]["note"]
    assert report["split"]["validation_year"] is None


def test_inference_returns_class_and_probabilities(trained):
    report, model_path, metrics_path, dataset = trained
    pending = dataset[dataset[TARGET_COLUMN].isna()]
    features = load_feature_list(metrics_path)
    model = joblib.load(model_path)
    result = predict_with_probabilities(model, pending[features])
    assert set(result["prediction"]) <= set(report["classes"])
    proba = result[[c for c in result.columns if c.startswith("proba_")]]
    assert proba.sum(axis=1).round(6).eq(1.0).all()
    series = predict(model_path, pending[features])
    assert isinstance(series, pd.Series) and len(series) == len(pending)
