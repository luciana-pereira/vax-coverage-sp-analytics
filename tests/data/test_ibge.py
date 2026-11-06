from pipeline.extract.ibge import fetch_population
from pipeline.extract.ibge_age import AGE_0_4, AGE_60_PLUS, build_target_population


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return [
            {"D1C": "Município", "D2C": "Ano", "D3C": "Variável", "V": "Valor"},
            {
                "D1C": "3500105",
                "D1N": "Adamantina",
                "D2C": "9324",
                "D3C": "2024",
                "V": "35265",
            },
        ]


def test_fetch_population_uses_sidra_variable_and_normalizes_rows(monkeypatch):
    requested = {}

    def fake_get(url, params=None, timeout=None):
        requested.update(url=url, params=params, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr("pipeline.extract.http.requests.get", fake_get)

    rows = fetch_population(
        year=2024,
        base_url="https://sidra.example",
        table=6579,
        variable=9324,
        timeout=15,
    )

    assert requested == {
        "url": "https://sidra.example/values/t/6579/n6/all/v/9324/p/2024",
        "params": None,
        "timeout": 15,
    }
    assert rows == [
        {
            "municipality_code": "350010",
            "ibge_code": "3500105",
            "municipality_name": "Adamantina",
            "year": 2024,
            "population": 35265,
        }
    ]


def test_target_population_requires_explicit_vaccine_age_mapping():
    import pandas as pd
    import pytest

    census_age = pd.DataFrame(
        [
            {
                "municipality_code": "350010",
                "municipality_name": "Adamantina",
                "year": 2022,
                "age_code": AGE_0_4,
                "population": 100,
            },
            {
                "municipality_code": "350010",
                "municipality_name": "Adamantina",
                "year": 2022,
                "age_code": AGE_60_PLUS[0],
                "population": 50,
            },
        ]
    )

    with pytest.raises(ValueError, match="faixa etária.*imunizante"):
        build_target_population(census_age)

    target = build_target_population(
        census_age,
        age_group_to_immunizer={"0_4": "approved-vaccine-a", "60_plus": "approved-vaccine-b"},
    )
    assert set(target["immunizer"]) == {"approved-vaccine-a", "approved-vaccine-b"}
