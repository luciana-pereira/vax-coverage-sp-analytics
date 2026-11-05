from pipeline.extract.ibge import fetch_population


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

    def fake_get(url, timeout):
        requested.update(url=url, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr("pipeline.extract.ibge.requests.get", fake_get)

    rows = fetch_population(
        year=2024,
        base_url="https://sidra.example",
        table=6579,
        variable=9324,
        timeout=15,
    )

    assert requested == {
        "url": "https://sidra.example/values/t/6579/n6/all/v/9324/p/2024",
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
