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
    for column in required_columns:
        if column in df.columns and df[column].isna().any():
            report.issues.append(f"'{column}' possui valores nulos")
    report.duplicate_rows = int(df.duplicated().sum())
    if report.duplicate_rows:
        report.issues.append(f"{report.duplicate_rows} linhas duplicadas")

    for column in ("doses", "population"):
        if column in df.columns:
            values = pd.to_numeric(df[column], errors="coerce")
            if values.isna().all():
                report.issues.append(f"'{column}' não possui valores numéricos")
            elif (df[column].notna() & values.isna()).any():
                report.issues.append(f"'{column}' possui valores não numéricos")
            elif (values < 0).any():
                report.issues.append(f"'{column}' possui valores negativos")

    if "population" in df.columns:
        population = pd.to_numeric(df["population"], errors="coerce")
        if (population == 0).any():
            report.issues.append("'population' possui valores zero (cobertura indefinida)")

    if "year" in df.columns and pd.to_numeric(df["year"], errors="coerce").isna().any():
        report.issues.append("'year' possui valores não numéricos")

    return report


def validate_population_alignment(
    dataset: pd.DataFrame,
    target_population: pd.DataFrame,
) -> list[str]:
    keys = ["municipality_code", "year", "immunizer"]
    required = {*keys, "population"}
    missing_dataset = required - set(dataset.columns)
    missing_target = required - set(target_population.columns)
    issues = []

    if missing_dataset:
        issues.append(f"dataset sem chaves/denominador: {sorted(missing_dataset)}")
    if missing_target:
        issues.append(f"população-alvo sem chaves/denominador: {sorted(missing_target)}")
    if issues:
        return issues

    actual = dataset[keys + ["population"]].copy()
    expected = target_population[keys + ["population"]].copy()
    actual = actual.rename(columns={"population": "population_dataset"})
    expected = expected.rename(columns={"population": "population_target"})

    for frame in (actual, expected):
        frame["municipality_code"] = (
            pd.to_numeric(frame["municipality_code"], errors="coerce")
            .astype("Int64")
            .astype("string")
        )
        frame["year"] = (
            pd.to_numeric(frame["year"], errors="coerce").astype("Int64").astype("string")
        )
        frame["immunizer"] = frame["immunizer"].astype("string").str.strip()
    actual["population_dataset"] = pd.to_numeric(actual["population_dataset"], errors="coerce")
    expected["population_target"] = pd.to_numeric(expected["population_target"], errors="coerce")

    if expected.duplicated(keys).any():
        issues.append("população-alvo possui chaves município/ano/immunizer duplicadas")
        return issues

    aligned = actual.merge(expected, on=keys, how="left", indicator=True)
    unmatched = int((aligned["_merge"] != "both").sum())
    if unmatched:
        issues.append(f"{unmatched} grupos município/ano/immunizer sem população-alvo")

    matched = aligned[aligned["_merge"] == "both"]
    mismatched = matched["population_dataset"] != matched["population_target"]
    if mismatched.any():
        issues.append(
            f"{int(mismatched.sum())} denominadores divergem da população-alvo configurada"
        )

    return issues
