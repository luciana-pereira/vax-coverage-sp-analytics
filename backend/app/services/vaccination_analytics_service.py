"""Monta respostas agregadas para vacinação, sem retornar registros individuais."""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from typing import Any

from ..repositories.vaccination_analytics_repository import (
    AnalyticsSnapshot,
    VaccinationAnalyticsRepository,
    _statewide,
    _vaccine_key,
    _vaccine_label,
    csv_snapshot,
    postgres_snapshot,
)
from ..schemas.analytics import (
    AnalyticsCategory,
    AnalyticsFilters,
    AnalyticsMonth,
    AnalyticsMunicipalityCount,
    AnalyticsMunicipalityFilter,
    AnalyticsUploadResponse,
    AnalyticsVaccineCount,
    AnalyticsVaccineFilter,
    VaccinationAnalyticsResponse,
)

_POSTGRES_FAILURES: dict[tuple[str, str], str] = {}


def _selected_year(year: int | None, years: list[int]) -> int | None:
    return year if year is not None else max(years, default=None)


def _matches_filters(
    row: dict[str, Any],
    year: int | None,
    vaccine: str | None,
    age_group: str | None,
    municipality_code: str | None,
    municipality_basis: str,
) -> bool:
    if year is not None and int(row["year"]) != year:
        return False
    if (
        vaccine is not None
        and _vaccine_key(
            row.get("vaccine_code"),
            row.get("vaccine_abbreviation"),
            row.get("vaccine_description"),
        )
        != vaccine
    ):
        return False
    if age_group is not None and row.get("age_group") != age_group:
        return False
    if municipality_code is not None:
        return row.get(f"{municipality_basis}_municipality_code") == municipality_code
    return True


@lru_cache(maxsize=3)
def _postgres_snapshot_cached(
    dsn: str, table: str, year: int
) -> tuple[AnalyticsSnapshot | None, str | None]:
    failure_key = (dsn, table)
    if failure_key in _POSTGRES_FAILURES:
        return None, _POSTGRES_FAILURES[failure_key]
    try:
        return postgres_snapshot(dsn, table, year), None
    except (RuntimeError, ValueError) as exc:
        message = str(exc)
        sanitized = message if len(message) <= 120 else "PostgreSQL indisponível."
        _POSTGRES_FAILURES[failure_key] = sanitized
        return None, sanitized


class VaccinationAnalyticsService:
    def __init__(self, repository: VaccinationAnalyticsRepository) -> None:
        self.repository = repository

    def _snapshot(self, year: int | None) -> tuple[AnalyticsSnapshot, list[str]]:
        dsn = next(
            (
                os.getenv(name)
                for name in ("VACCINATION_DATABASE_URL", "AIVEN_DATABASE_URL", "DATABASE_URL")
                if os.getenv(name)
            ),
            None,
        )
        warnings: list[str] = []
        if dsn:
            table = os.getenv("VACCINATION_TABLE", "public.vaccination")
            target_year = year or 2024
            snapshot, error = _postgres_snapshot_cached(dsn, table, target_year)
            if snapshot:
                return snapshot, warnings
            warnings.append(error or "PostgreSQL indisponível.")
        return self.repository.local_snapshot(), warnings

    def analytics(
        self,
        year: int | None = None,
        vaccine: str | None = None,
        age_group: str | None = None,
        municipality_code: str | None = None,
        municipality_basis: str = "patient",
        snapshot: AnalyticsSnapshot | None = None,
    ) -> VaccinationAnalyticsResponse:
        warnings: list[str] = []
        if snapshot is None:
            snapshot, warnings = self._snapshot(year)
        rows = list(snapshot.rows)
        years = sorted({int(row["year"]) for row in rows if row.get("year") is not None})
        selected_year = _selected_year(year, years)
        all_vaccines = _vaccine_filters(rows)
        filtered = [
            row
            for row in rows
            if _matches_filters(
                row, selected_year, vaccine, age_group, municipality_code, municipality_basis
            )
        ]

        patient_municipalities = _municipality_filters(rows, "patient")
        application_municipalities = _municipality_filters(rows, "application")
        statewide = _statewide(rows)
        dimensions = dict(snapshot.dimensions)
        dimensions["sex"] = dimensions.get("sex", False) and any(row.get("sex") for row in rows)
        dimensions["age"] = dimensions.get("age", False) and any(
            row.get("age_group") for row in rows
        )
        dimensions["patient_municipality"] = bool(patient_municipalities)
        dimensions["application_municipality"] = bool(application_municipalities)
        dimensions["municipality_comparison"] = statewide
        monthly = _monthly(filtered)

        if not rows:
            return VaccinationAnalyticsResponse(
                status="data_unavailable",
                message="Nenhum dado agregado disponível para a fonte selecionada.",
                generated_at=datetime.now().astimezone(),
                warnings=warnings,
            )

        return VaccinationAnalyticsResponse(
            status="ok",
            source=snapshot.source,
            source_updated_at=snapshot.source_updated_at,
            generated_at=datetime.now().astimezone(),
            year=selected_year,
            period_start=monthly[0].month if monthly else None,
            period_end=monthly[-1].month if monthly else None,
            total_doses=sum(int(row["doses"]) for row in filtered),
            statewide=statewide,
            dimensions=dimensions,
            filters=AnalyticsFilters(
                years=years,
                vaccines=all_vaccines,
                age_groups=sorted(
                    {
                        str(row["age_group"])
                        for row in rows
                        if row.get("age_group") in {"0-4", "60+"}
                    }
                ),
                patient_municipalities=patient_municipalities,
                application_municipalities=application_municipalities,
            ),
            monthly=monthly,
            by_sex=_categories(filtered, "sex", {"M": "Masculino", "F": "Feminino"}),
            by_age_group=_categories(filtered, "age_group"),
            by_vaccine=_vaccine_counts(filtered),
            by_patient_municipality=(
                _municipality_counts(filtered, "patient") if statewide else []
            ),
            by_application_municipality=(
                _municipality_counts(filtered, "application") if statewide else []
            ),
            warnings=[*warnings, *snapshot.warnings],
        )

    def upload_csv(self, content: bytes) -> AnalyticsUploadResponse:
        snapshot = csv_snapshot(content)
        response = self.analytics(snapshot=snapshot)
        return AnalyticsUploadResponse(**response.model_dump(), accepted_rows=snapshot.total_rows)


def _monthly(rows: list[dict[str, Any]]) -> list[AnalyticsMonth]:
    counts: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        key = f"{int(row['year']):04d}-{int(row['month']):02d}"
        counts[key] += int(row["doses"])
    return [AnalyticsMonth(month=key, doses=value) for key, value in sorted(counts.items())]


def _categories(
    rows: list[dict[str, Any]], field: str, known_labels: dict[str, str] | None = None
) -> list[AnalyticsCategory]:
    counts: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        value = row.get(field)
        if value is not None:
            counts[str(value)] += int(row["doses"])
    labels = known_labels or {}
    return [
        AnalyticsCategory(key=key, label=labels.get(key, key), doses=value)
        for key, value in sorted(counts.items())
    ]


def _vaccine_filters(rows: list[dict[str, Any]]) -> list[AnalyticsVaccineFilter]:
    values: dict[str, AnalyticsVaccineFilter] = {}
    for row in rows:
        code = row.get("vaccine_code")
        abbreviation = row.get("vaccine_abbreviation")
        description = row.get("vaccine_description")
        key = _vaccine_key(code, abbreviation, description)
        values[key] = AnalyticsVaccineFilter(
            key=key,
            code=code,
            abbreviation=abbreviation,
            description=description,
            label=_vaccine_label(code, abbreviation, description),
        )
    return sorted(values.values(), key=lambda item: item.label.casefold())


def _vaccine_counts(rows: list[dict[str, Any]]) -> list[AnalyticsVaccineCount]:
    counts: defaultdict[str, int] = defaultdict(int)
    values: dict[str, tuple[Any, Any, Any]] = {}
    for row in rows:
        code = row.get("vaccine_code")
        abbreviation = row.get("vaccine_abbreviation")
        description = row.get("vaccine_description")
        key = _vaccine_key(code, abbreviation, description)
        values[key] = (code, abbreviation, description)
        counts[key] += int(row["doses"])
    return sorted(
        [
            AnalyticsVaccineCount(
                key=key,
                code=values[key][0],
                abbreviation=values[key][1],
                description=values[key][2],
                label=_vaccine_label(*values[key]),
                doses=count,
            )
            for key, count in counts.items()
        ],
        key=lambda item: (-item.doses, item.label.casefold()),
    )


def _municipality_filters(
    rows: list[dict[str, Any]], basis: str
) -> list[AnalyticsMunicipalityFilter]:
    code_field = f"{basis}_municipality_code"
    name_field = f"{basis}_municipality_name"
    values: dict[str, str | None] = {}
    for row in rows:
        code = row.get(code_field)
        if code:
            values[str(code)] = row.get(name_field)
    return [
        AnalyticsMunicipalityFilter(code=code, name=name)
        for code, name in sorted(values.items(), key=lambda item: (item[1] or item[0]).casefold())
    ]


def _municipality_counts(
    rows: list[dict[str, Any]], basis: str
) -> list[AnalyticsMunicipalityCount]:
    code_field = f"{basis}_municipality_code"
    name_field = f"{basis}_municipality_name"
    counts: defaultdict[str, int] = defaultdict(int)
    names: dict[str, str | None] = {}
    for row in rows:
        code = row.get(code_field)
        if code:
            key = str(code)
            names[key] = row.get(name_field)
            counts[key] += int(row["doses"])
    return sorted(
        [
            AnalyticsMunicipalityCount(code=code, name=names[code], doses=count)
            for code, count in counts.items()
        ],
        key=lambda item: (-item.doses, (item.name or item.code).casefold()),
    )
