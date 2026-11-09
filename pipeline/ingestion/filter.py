from __future__ import annotations

import pandas as pd


def filter_pni_chunk(
    df: pd.DataFrame,
    uf: str = "SP",
) -> pd.DataFrame:
    """Filtra um chunk do PNI para os grupos de análise do projeto."""

    required = {
        "co_paciente",
        "co_municipio_paciente",
        "no_municipio_paciente",
        "sg_uf_paciente",
        "sg_imunobiologico",
        "dt_vacina",
        "co_dose_vacina",
        "ds_tipo_dose",
        "nu_idade_paciente",
    }

    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Colunas obrigatórias ausentes no chunk PNI: {sorted(missing)}")

    result = df.copy()

    result["nu_idade_paciente"] = pd.to_numeric(
        result["nu_idade_paciente"],
        errors="coerce",
    )

    result = result[result["sg_uf_paciente"].eq(uf)]

    target = (result["nu_idade_paciente"].between(0, 4) & result["sg_imunobiologico"].eq("SCR")) | (
        result["nu_idade_paciente"].ge(60) & result["sg_imunobiologico"].eq("INF3")
    )

    return result.loc[target].copy()
