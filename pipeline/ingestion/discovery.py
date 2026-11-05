from __future__ import annotations

from pathlib import Path


def discover_pni_csvs(year_dir: Path) -> list[Path]:
    """Localiza arquivos CSV mensais do PNI para um determinado ano."""

    if not year_dir.exists():
        return []

    return sorted(
        path
        for path in year_dir.glob("*/*.csv")
        if path.is_file()
    )