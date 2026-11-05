import pandas as pd
import pytest

from ml.evaluation.evaluate import classification_metrics, load_metrics


def test_classification_metrics_known_values():
    y_true = pd.Series(["a", "a", "b", "b"])
    y_pred = ["a", "b", "b", "b"]
    metrics = classification_metrics(y_true, y_pred, ["a", "b"])
    assert metrics["accuracy"] == 0.75
    assert metrics["confusion_matrix"] == [[1, 1], [0, 2]]
    assert metrics["recall_macro"] == pytest.approx((0.5 + 1.0) / 2)
    assert metrics["precision_macro"] == pytest.approx((1.0 + 2 / 3) / 2)


def test_missing_class_in_predictions_does_not_break_metrics():
    metrics = classification_metrics(pd.Series(["a", "b"]), ["a", "a"], ["a", "b", "c"])
    assert len(metrics["confusion_matrix"]) == 3


def test_load_metrics_reads_json(tmp_path):
    path = tmp_path / "m.json"
    path.write_text('{"best_model": "x"}', encoding="utf-8")
    assert load_metrics(path)["best_model"] == "x"
