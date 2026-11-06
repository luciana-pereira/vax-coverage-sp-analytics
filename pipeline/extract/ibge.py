from __future__ import annotations

from .http import get_with_retry


def fetch_population(
    year: int,
    base_url: str = "https://apisidra.ibge.gov.br",
    table: int = 6579,
    variable: int = 9324,
    timeout: int = 120,
) -> list[dict]:
    url = f"{base_url.rstrip('/')}/values/t/{table}/n6/all/v/{variable}/p/{year}"

    response = get_with_retry(url, timeout=timeout)

    payload = response.json()

    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("Resposta inesperada da API SIDRA.")

    rows = payload[1:]

    return [
        {
            "municipality_code": row["D1C"][:6],
            "ibge_code": row["D1C"],
            "municipality_name": row["D1N"],
            "year": int(row["D3C"]),
            "population": int(row["V"]),
        }
        for row in rows
        if row.get("D2C") == str(variable)
        and row.get("D1C", "").startswith("35")
    ]

def fetch_census_age_structure(
    base_url: str = "https://apisidra.ibge.gov.br",
) -> list[dict]:
    """Busca a população municipal de SP por idade no Censo 2022."""
    url = (
        f"{base_url.rstrip('/')}"
        "/values/t/9514/n6/in%20n3%2035/p/2022"
    )

    response = get_with_retry(url, timeout=120)

    payload = response.json()

    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(
            "Resposta inesperada da API SIDRA para a estrutura etária."
        )

    return payload[1:]
