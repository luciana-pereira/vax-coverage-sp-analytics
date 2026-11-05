"""Regras de negócio de municípios."""

from __future__ import annotations

from typing import Any

from ..core.errors import NotFoundError
from ..repositories.coverage_repository import CoverageFilter, CoverageRepository
from ..schemas.municipality import (
    ImmunizerSummary,
    MunicipalityDetailResponse,
    MunicipalityItem,
    MunicipalityListResponse,
)
from .coverage_service import classify_deficit, history_point, round_value, unavailable_message


def _item(row: dict[str, Any]) -> MunicipalityItem:
    return MunicipalityItem(
        municipality_code=row["municipality_code"],
        municipality_name=row["municipality_name"],
        mean_coverage=round_value(row["mean_coverage"]),
        mean_deficit=round_value(row["mean_deficit"]),
        deficit_class=classify_deficit(row["mean_deficit"]),
        records=row["records"],
    )


class MunicipalityService:
    def __init__(self, repo: CoverageRepository) -> None:
        self.repo = repo

    def list(self, flt: CoverageFilter, limit: int, offset: int) -> MunicipalityListResponse:
        message = unavailable_message(self.repo)
        if message:
            return MunicipalityListResponse(
                status="data_unavailable", message=message, limit=limit, offset=offset
            )
        total, rows = self.repo.municipalities(flt, limit, offset)
        return MunicipalityListResponse(
            status="ok",
            total=total,
            limit=limit,
            offset=offset,
            items=[_item(r) for r in rows],
        )

    def detail(self, code: str, flt: CoverageFilter) -> MunicipalityDetailResponse:
        message = unavailable_message(self.repo)
        if message:
            raise NotFoundError(message)
        scoped = CoverageFilter(
            year=flt.year,
            year_from=flt.year_from,
            year_to=flt.year_to,
            immunizer=flt.immunizer,
            municipality_codes=[code],
            deficit_class=flt.deficit_class,
        )
        _, rows = self.repo.municipalities(scoped, 1, 0)
        if not rows:
            raise NotFoundError(f"Município {code} sem registros.")
        history = self.repo.history(scoped, by_municipality=False)
        by_immunizer = self.repo.by_immunizer(scoped)
        return MunicipalityDetailResponse(
            municipality=_item(rows[0]),
            history=[history_point(r) for r in history],
            by_immunizer=[
                ImmunizerSummary(
                    immunizer=r["immunizer"],
                    mean_coverage=round_value(r["mean_coverage"]),
                    mean_deficit=round_value(r["mean_deficit"]),
                )
                for r in by_immunizer
            ],
        )
