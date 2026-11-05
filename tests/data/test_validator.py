import pandas as pd

from pipeline.config import REQUIRED_COLUMNS
from pipeline.validate.validator import validate_dataset


def _ok_frame():
    return pd.DataFrame(
        {
            "municipality_code": ["1", "2"],
            "year": [2020, 2020],
            "doses": [5, 6],
            "population": [10, 20],
        }
    )


def test_valid_dataset_has_no_issues():
    report = validate_dataset(_ok_frame(), REQUIRED_COLUMNS)
    assert report.ok and report.rows == 2


def test_missing_columns_are_reported():
    report = validate_dataset(_ok_frame().drop(columns=["population"]), REQUIRED_COLUMNS)
    assert not report.ok and report.missing_columns == ["population"]


def test_negative_zero_population_and_duplicates_are_flagged():
    df = pd.concat([_ok_frame(), _ok_frame().iloc[[0]]], ignore_index=True)
    df.loc[1, "doses"] = -1
    df.loc[1, "population"] = 0
    issues = " ".join(validate_dataset(df, REQUIRED_COLUMNS).issues)
    assert "negativos" in issues and "zero" in issues and "duplicadas" in issues


def test_empty_dataset_is_invalid():
    assert not validate_dataset(pd.DataFrame(columns=list(REQUIRED_COLUMNS)), REQUIRED_COLUMNS).ok
