"""Validação de qualidade do dataset processado."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationReport:
    rows: int
    missing_columns: list[str] = field(default_factory=list)
    null_counts: dict[str, int] = field(default_factory=dict)
    duplicate_rows: int = 0
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def validate_dataset(df: pd.DataFrame, required_columns: tuple[str, ...]) -> ValidationReport:
    report = ValidationReport(rows=len(df))
    report.missing_columns = [c for c in required_columns if c not in df.columns]
    if report.missing_columns:
        report.issues.append(f"colunas obrigatórias ausentes: {report.missing_columns}")

    if df.empty:
        report.issues.append("dataset vazio")
        return report

    report.null_counts = {c: int(n) for c, n in df.isna().sum().items() if n}
    report.duplicate_rows = int(df.duplicated().sum())
    if report.duplicate_rows:
        report.issues.append(f"{report.duplicate_rows} linhas duplicadas")

    for column in ("doses", "population"):
        if column in df.columns:
            values = pd.to_numeric(df[column], errors="coerce")
            if values.isna().all():
                report.issues.append(f"'{column}' não possui valores numéricos")
            elif (values < 0).any():
                report.issues.append(f"'{column}' possui valores negativos")

    if "population" in df.columns:
        population = pd.to_numeric(df["population"], errors="coerce")
        if (population == 0).any():
            report.issues.append("'population' possui valores zero (cobertura indefinida)")

    if "year" in df.columns and pd.to_numeric(df["year"], errors="coerce").isna().any():
        report.issues.append("'year' possui valores não numéricos")

    return report
