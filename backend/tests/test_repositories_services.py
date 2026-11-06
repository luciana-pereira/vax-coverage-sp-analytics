import pytest

from app.repositories.coverage_repository import CoverageFilter, CoverageRepository
from app.services.coverage_service import classify_deficit, unavailable_message


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (0.0, "baixo"),
        (5.0, "baixo"),
        (5.01, "moderado"),
        (15.0, "moderado"),
        (15.5, "alto"),
    ],
)
def test_classify_deficit_boundaries(value, expected):
    assert classify_deficit(value) == expected


def test_repository_missing_file(tmp_path):
    repo = CoverageRepository(tmp_path / "nope.parquet")
    assert not repo.exists and repo.columns() == []
    assert "ausente" in unavailable_message(repo)


def test_repository_reports_missing_columns(tmp_path):
    import pandas as pd

    path = tmp_path / "partial.parquet"
    pd.DataFrame({"municipality_code": ["1"], "year": [2020]}).to_parquet(path)
    repo = CoverageRepository(path)
    assert set(repo.missing_columns()) == {"coverage", "deficit", "deficit_class", "immunizer"}
    assert "colunas" in unavailable_message(repo)


@pytest.mark.usefixtures("features_file")
def test_repository_aggregations(settings):
    repo = CoverageRepository(settings.features_path)
    total, rows = repo.municipalities(CoverageFilter(), 10, 0, order_by_deficit=True)
    assert total == 3 and rows[0]["municipality_code"] == "3300"
    history = repo.history(CoverageFilter(municipality_codes=["1100"]), by_municipality=True)
    assert [h["year"] for h in history] == [2022, 2023]
    assert repo.by_immunizer(CoverageFilter(year=2023))[0]["immunizer"] == "X"
    quality = repo.quality()
    assert quality["rows"] == 5
    assert quality["records_by_year"] == [
        {"year": 2022, "records": 2},
        {"year": 2023, "records": 3},
    ]


@pytest.mark.usefixtures("features_file")
def test_repository_filters_are_parameterized(settings):
    repo = CoverageRepository(settings.features_path)
    hostile = CoverageFilter(immunizer="X' OR '1'='1")
    assert repo.summary(hostile, "alto")["records"] == 0
