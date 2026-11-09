from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .http import get_with_retry

CENSUS_TABLE = 9514
CENSUS_VARIABLE = 93

AGE_0_4 = "93070"

AGE_60_PLUS = (
    "93095",
    "93096",
    "93097",
    "93098",
    "49108",
    "49109",
    "60040",
    "60041",
    "6653",
)


def fetch_census_age_population(
    base_url: str = "https://apisidra.ibge.gov.br",
    year: int = 2022,
    uf: str = "35",
    timeout: int = 120,
) -> pd.DataFrame:
    """Busca população municipal de SP por faixa etária no Censo 2022."""

    age_codes = (AGE_0_4,) + AGE_60_PLUS
    codes = ",".join(age_codes)

    url = (
        f"{base_url.rstrip('/')}"
        f"/values/t/{CENSUS_TABLE}"
        f"/n6/in%20n3%20{uf}"
        f"/p/{year}"
        f"/v/{CENSUS_VARIABLE}"
        f"/c287/{codes}"
    )

    response = get_with_retry(url, timeout=timeout)

    payload = response.json()

    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("Resposta inesperada da API SIDRA para estrutura etária.")

    rows = payload[1:]

    records = []

    for row in rows:
        municipality_code = row.get("D1C")
        age_code = row.get("D4C")
        value = row.get("V")

        if not municipality_code or age_code not in age_codes:
            continue

        records.append(
            {
                "municipality_code": municipality_code[:6],
                "municipality_name": row["D1N"],
                "year": int(row["D2C"]),
                "age_code": age_code,
                "population": int(value) if value not in {None, "-"} else 0,
            }
        )

    df = pd.DataFrame(records)

    if df.empty:
        raise ValueError("Nenhuma população etária foi retornada pelo SIDRA.")

    return df


def build_target_population(
    census_age: pd.DataFrame,
    age_group_to_immunizer: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Build target populations only with an explicitly approved age mapping."""

    if not age_group_to_immunizer:
        raise ValueError(
            "É necessário validar e fornecer o mapeamento de faixa etária para imunizante."
        )

    required = {
        "municipality_code",
        "municipality_name",
        "year",
        "age_code",
        "population",
    }

    missing = required - set(census_age.columns)

    if missing:
        raise KeyError(f"Colunas ausentes na população etária: {sorted(missing)}")

    result = (
        census_age.assign(
            age_group=lambda df: df["age_code"].map(
                lambda code: "0_4" if code == AGE_0_4 else "60_plus"
            )
        )
        .groupby(
            [
                "municipality_code",
                "municipality_name",
                "year",
                "age_group",
            ],
            as_index=False,
        )["population"]
        .sum()
    )

    unmapped = set(result["age_group"]) - set(age_group_to_immunizer)
    if unmapped:
        raise ValueError(f"Faixas etárias sem imunizante validado: {sorted(unmapped)}")
    result["immunizer"] = result["age_group"].map(age_group_to_immunizer)

    return result[
        [
            "municipality_code",
            "municipality_name",
            "year",
            "immunizer",
            "population",
        ]
    ]


def estimate_target_population(
    census_target: pd.DataFrame,
    total_population_2022: pd.DataFrame,
    total_population_2024: pd.DataFrame,
) -> pd.DataFrame:
    """Estima a população-alvo de 2024 a partir da estrutura etária de 2022."""

    required_target = {
        "municipality_code",
        "municipality_name",
        "year",
        "immunizer",
        "population",
    }

    if not required_target.issubset(census_target.columns):
        missing = required_target - set(census_target.columns)
        raise KeyError(f"Colunas ausentes na população-alvo: {sorted(missing)}")

    for frame, name in (
        (total_population_2022, "população total 2022"),
        (total_population_2024, "população total 2024"),
    ):
        required = {"municipality_code", "population"}
        if not required.issubset(frame.columns):
            missing = required - set(frame.columns)
            raise KeyError(f"Colunas ausentes em {name}: {sorted(missing)}")

    base = census_target.copy()

    pop_2022 = total_population_2022[["municipality_code", "population"]].rename(
        columns={"population": "total_population_2022"}
    )

    pop_2024 = total_population_2024[["municipality_code", "population"]].rename(
        columns={"population": "total_population_2024"}
    )

    result = base.merge(pop_2022, on="municipality_code", how="inner").merge(
        pop_2024, on="municipality_code", how="inner"
    )

    result["population_share_2022"] = result["population"] / result["total_population_2022"]

    result["population"] = (
        (result["population_share_2022"] * result["total_population_2024"]).round().astype(int)
    )

    result["year"] = 2024

    return result[
        [
            "municipality_code",
            "municipality_name",
            "year",
            "immunizer",
            "population",
        ]
    ]
