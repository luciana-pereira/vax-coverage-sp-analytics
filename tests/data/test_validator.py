import pandas as pd

from pipeline.config import REQUIRED_COLUMNS
from pipeline.validate.validator import validate_dataset, validate_population_alignment


def _ok_frame():
    return pd.DataFrame(
        {
            "municipality_code": ["1", "2"],
            "immunizer": ["BCG", "SCR"],
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


def test_missing_immunizer_column_is_invalid():
    report = validate_dataset(_ok_frame().drop(columns=["immunizer"]), REQUIRED_COLUMNS)
    assert not report.ok and report.missing_columns == ["immunizer"]


def test_null_required_population_is_invalid():
    frame = _ok_frame()
    frame.loc[0, "population"] = None

    report = validate_dataset(frame, REQUIRED_COLUMNS)

    assert not report.ok
    assert "population" in " ".join(report.issues)


def test_negative_zero_population_and_duplicates_are_flagged():
    df = pd.concat([_ok_frame(), _ok_frame().iloc[[0]]], ignore_index=True)
    df.loc[1, "doses"] = -1
    df.loc[1, "population"] = 0
    issues = " ".join(validate_dataset(df, REQUIRED_COLUMNS).issues)
    assert "negativos" in issues and "zero" in issues and "duplicadas" in issues


def test_empty_dataset_is_invalid():
    assert not validate_dataset(pd.DataFrame(columns=list(REQUIRED_COLUMNS)), REQUIRED_COLUMNS).ok


def test_population_alignment_requires_exact_municipality_year_and_immunizer_target():
    vaccination = pd.DataFrame(
        {
            "municipality_code": ["350010", "350010"],
            "year": [2024, 2024],
            "immunizer": ["SCR", "INF3"],
            "population": [10, 20],
        }
    )
    targets = vaccination.copy()

    assert validate_population_alignment(vaccination, targets) == []

    targets.loc[1, "population"] = 30
    issues = validate_population_alignment(vaccination, targets)
    assert any("divergem" in issue for issue in issues)


def test_population_alignment_rejects_missing_immunizer_and_duplicate_targets():
    vaccination = pd.DataFrame(
        {
            "municipality_code": ["350010"],
            "year": [2024],
            "immunizer": ["SCR"],
            "population": [10],
        }
    )
    targets = vaccination.drop(columns=["immunizer"])

    assert any(
        "immunizer" in issue
        for issue in validate_population_alignment(vaccination, targets)
    )

    duplicated = pd.concat([vaccination, vaccination], ignore_index=True)
    assert any(
        "duplicadas" in issue
        for issue in validate_population_alignment(vaccination, duplicated)
    )
