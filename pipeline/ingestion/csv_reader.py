from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd

PNI_COLUMNS = (
    "co_paciente",
    "co_municipio_paciente",
    "no_municipio_paciente",
    "sg_uf_paciente",
    "co_vacina",
    "sg_imunobiologico",
    "dt_vacina",
    "co_dose_vacina",
    "ds_tipo_dose",
    "nu_idade_paciente",
)


def read_pni_csv(
    path: Path,
    chunksize: int = 100_000,
) -> Iterator[pd.DataFrame]:
    """Lê um CSV mensal do PNI em blocos, sem carregar o arquivo inteiro."""

    if not path.exists():
        raise FileNotFoundError(f"Arquivo PNI não encontrado: {path}")

    if path.suffix.lower() != ".csv":
        raise ValueError(f"Arquivo PNI deve ser CSV: {path}")

    for chunk in pd.read_csv(
        path,
        sep=";",
        encoding="latin-1",
        chunksize=chunksize,
        low_memory=False,
        usecols=lambda column: column in PNI_COLUMNS,
    ):
        yield chunk
