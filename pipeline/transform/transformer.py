import json
from pathlib import Path

import pandas as pd


def load_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return pd.json_normalize(rows)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        str(c).strip().lower().replace(" ", "_").replace("-", "_")
        for c in df.columns
    ]
    return df

def transform(df: pd.DataFrame, deduplicate: bool = True) -> pd.DataFrame:
    df = normalize_columns(df)
    # O schema da API pode mudar. A normalização acima é intencionalmente
    # genérica; o mapeamento definitivo deve ser fechado após inspeção do
    # dicionário de dados/endpoints escolhidos pelo grupo.
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype("string").str.strip()
    # Linhas idênticas podem ser registros legítimos se a fonte for por registro.
    return df.drop_duplicates() if deduplicate else df


def apply_column_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Renomeia colunas da fonte para o esquema canônico (`canônica -> fonte`)."""
    missing = [source for source in mapping.values() if source not in df.columns]
    if missing:
        raise KeyError(f"Colunas do mapeamento ausentes na fonte: {missing}")
    rename = {source: canonical for canonical, source in mapping.items()}
    return df.rename(columns=rename)

def attach_target_population(
    df: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    """Agrega doses e anexa a população-alvo municipal."""

    if not {"municipality_code", "year", "population"}.issubset(
        population.columns
    ):
        raise KeyError(
            "População-alvo exige municipality_code, year e population."
        )

    if "immunizer" in df.columns and "immunizer" not in population.columns:
        raise KeyError(
            "População-alvo por imunizante exige a coluna 'immunizer'; "
            "população municipal total não é denominador universal."
        )

    required = {"municipality_code", "year", "doses"}
    missing = required - set(df.columns)

    if missing:
        raise KeyError(
            f"Colunas de junção ausentes nos dados de vacinação: {sorted(missing)}"
        )

    left = df.drop(columns=["population"], errors="ignore").copy()
    join_cols = ["municipality_code", "year"]
    if "immunizer" in left.columns and "immunizer" in population.columns:
        join_cols.append("immunizer")

    if population.duplicated(subset=join_cols).any():
        raise ValueError(
            f"População-alvo possui chaves duplicadas: {join_cols}. "
            "Corrija o arquivo antes do join."
        )

    right = population[join_cols + ["population"]].copy()

    # Normaliza os códigos municipais para evitar valores como 350010.0.
    left["municipality_code"] = (
        pd.to_numeric(left["municipality_code"], errors="coerce")
        .astype("Int64")
        .astype("string")
    )

    right["municipality_code"] = (
        pd.to_numeric(right["municipality_code"], errors="coerce")
        .astype("Int64")
        .astype("string")
    )

    left["year"] = pd.to_numeric(
        left["year"],
        errors="coerce",
    ).astype("Int64").astype("string")

    right["year"] = pd.to_numeric(
        right["year"],
        errors="coerce",
    ).astype("Int64").astype("string")

    left["doses"] = pd.to_numeric(
        left["doses"],
        errors="coerce",
    )

    # Mantém immunizer quando ele existir no dataset do PNI,
    # mesmo que a população do IBGE seja municipal e não por imunizante.
    group_cols = [
        "municipality_code",
        "year",
    ]

    if "municipality_name" in left.columns:
        group_cols.append("municipality_name")

    if "immunizer" in left.columns:
        group_cols.append("immunizer")

    grouped = (
        left.groupby(
            group_cols,
            dropna=False,
            as_index=False,
        )["doses"]
        .sum()
    )

    return grouped.merge(
        right,
        on=join_cols,
        how="left",
    )
