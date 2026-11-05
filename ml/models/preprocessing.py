"""Transformações de pré-processamento serializadas junto ao modelo."""

from __future__ import annotations

import numpy as np
import pandas as pd


def to_object_nan(X) -> pd.DataFrame:
    """Normaliza ausentes (None/pd.NA) para NaN em colunas categóricas."""
    frame = pd.DataFrame(X).astype(object)
    return frame.where(frame.notna(), np.nan)
