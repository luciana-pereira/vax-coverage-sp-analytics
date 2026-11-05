import pandas as pd

from ml.features.build_features import (
    TARGET_COLUMN,
    build_ml_dataset,
    build_vaccination_features,
    feature_columns,
)


def test_deficit():
    df = pd.DataFrame({
        "doses": [80],
        "population": [100],
        "year": [2024],
    })
    out = build_vaccination_features(df, "doses", "population", "year", meta=95)
    assert out.loc[0, "coverage"] == 80
    assert out.loc[0, "deficit"] == 15
    assert out.loc[0, "deficit_class"] == "moderado"


def test_coverage_is_nan_when_population_is_zero():
    df = pd.DataFrame({"doses": [10], "population": [0], "year": [2024]})
    out = build_vaccination_features(df, "doses", "population", "year")
    assert pd.isna(out.loc[0, "coverage"])


def test_deficit_never_negative_and_classes():
    df = pd.DataFrame({"doses": [120, 92, 50], "population": [100, 100, 100], "year": [2024] * 3})
    out = build_vaccination_features(df, "doses", "population", "year", meta=95)
    assert (out["deficit"] >= 0).all()
    assert out["deficit_class"].tolist() == ["baixo", "baixo", "alto"]


def test_target_is_configurable_per_immunizer():
    df = pd.DataFrame(
        {
            "immunizer": ["A", "B"],
            "doses": [80, 80],
            "population": [100, 100],
            "year": [2024, 2024],
        }
    )
    out = build_vaccination_features(
        df, "doses", "population", "year", meta=95, immunizer_col="immunizer", targets={"A": 90}
    )
    assert out["coverage_target"].tolist() == [90.0, 95.0]
    assert out["deficit"].tolist() == [10.0, 15.0]


def test_ml_dataset_target_is_next_year_class(processed_frame):
    features = build_vaccination_features(processed_frame, "doses", "population", "year")
    dataset = build_ml_dataset(features)
    keys = ["municipality_code", "immunizer"]
    mask = (features["municipality_code"] == "3500000") & (features["immunizer"] == "VAC_A")
    sample = features[mask]
    sample = sample.sort_values("year").reset_index(drop=True)
    row = dataset[
        (dataset["municipality_code"] == "3500000")
        & (dataset["immunizer"] == "VAC_A")
        & (dataset["year"] == 2019)
    ].iloc[0]
    assert row[TARGET_COLUMN] == str(sample.loc[1, "deficit_class"])
    assert pd.isna(row["coverage_prev"])
    last = dataset[dataset["year"] == dataset["year"].max()]
    assert last[TARGET_COLUMN].isna().all()
    assert len(dataset) == len(features) and keys


def test_feature_columns_exclude_target_and_current_class(processed_frame):
    features = build_vaccination_features(processed_frame, "doses", "population", "year")
    cols = feature_columns(build_ml_dataset(features))
    assert "deficit_class" not in cols and TARGET_COLUMN not in cols
