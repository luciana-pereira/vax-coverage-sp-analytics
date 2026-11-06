import pandas as pd
import pytest

from pipeline.transform.transformer import (
    apply_column_mapping,
    attach_target_population,
    normalize_columns,
    transform,
)


def test_normalize_columns():
    df = pd.DataFrame({"Nome Município": ["São Paulo"], "Ano-Vacina": [2024]})
    out = normalize_columns(df)
    assert "nome_município" in out.columns
    assert "ano_vacina" in out.columns

def test_transform_removes_duplicates():
    df = pd.DataFrame({"a": [1, 1], "b": ["x", "x"]})
    assert len(transform(df)) == 1


def test_apply_column_mapping_renames_to_canonical():
    df = pd.DataFrame({"cod": ["1"], "ano_x": [2020], "qtd": [10]})
    mapping = {"municipality_code": "cod", "year": "ano_x", "doses": "qtd"}
    out = apply_column_mapping(df, mapping)
    assert set(out.columns) == {"municipality_code", "year", "doses"}


def test_apply_column_mapping_fails_on_missing_source_column():
    with pytest.raises(KeyError):
        apply_column_mapping(pd.DataFrame({"a": [1]}), {"doses": "inexistente"})


def test_attach_target_population_sums_doses_and_joins():
    df = pd.DataFrame(
        {
            "municipality_code": ["1", "1", "2"],
            "year": [2020, 2020, 2020],
            "doses": [3, 7, 5],
        }
    )
    population = pd.DataFrame(
        {"municipality_code": ["1", "2"], "year": [2020, 2020], "population": [20, 50]}
    )
    out = attach_target_population(df, population).sort_values("municipality_code")
    assert out["doses"].tolist() == [10, 5]
    assert out["population"].tolist() == [20, 50]


def test_attach_target_population_matches_immunizer_when_available():
    df = pd.DataFrame(
        {
            "municipality_code": ["1", "1"],
            "year": [2024, 2024],
            "immunizer": ["SCR", "INF3"],
            "doses": [7, 5],
        }
    )
    population = pd.DataFrame(
        {
            "municipality_code": ["1", "1"],
            "year": [2024, 2024],
            "immunizer": ["SCR", "INF3"],
            "population": [10, 20],
        }
    )

    out = attach_target_population(df, population).sort_values("immunizer")

    assert out["immunizer"].tolist() == ["INF3", "SCR"]
    assert out["population"].tolist() == [20, 10]


def test_attach_target_population_rejects_universal_population_for_immunizers():
    vaccination = pd.DataFrame(
        {
            "municipality_code": ["350010"],
            "year": [2024],
            "immunizer": ["SCR"],
            "doses": [1],
        }
    )
    municipal_total = pd.DataFrame(
        {
            "municipality_code": ["350010"],
            "year": [2024],
            "population": [35642],
        }
    )

    with pytest.raises(KeyError, match="immunizer"):
        attach_target_population(vaccination, municipal_total)


def test_attach_target_population_rejects_duplicate_target_keys():
    vaccination = pd.DataFrame(
        {
            "municipality_code": ["350010"],
            "year": [2024],
            "immunizer": ["SCR"],
            "doses": [1],
        }
    )
    targets = pd.DataFrame(
        {
            "municipality_code": ["350010", "350010"],
            "year": [2024, 2024],
            "immunizer": ["SCR", "SCR"],
            "population": [10, 11],
        }
    )

    with pytest.raises(ValueError, match="duplicadas"):
        attach_target_population(vaccination, targets)


def test_attach_target_population_requires_keys():
    with pytest.raises(KeyError):
        attach_target_population(pd.DataFrame({"doses": [1]}), pd.DataFrame({"x": [1]}))


def test_transform_can_keep_identical_rows():
    df = pd.DataFrame({"a": [1, 1], "b": ["x", "x"]})
    assert len(transform(df, deduplicate=False)) == 2
