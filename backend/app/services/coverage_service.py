"""Regras de negócio de cobertura e série histórica."""

from __future__ import annotations

from typing import Any

from ml.features.build_features import DEFICIT_BINS, DEFICIT_LABELS

from ..repositories.coverage_repository import CoverageFilter, CoverageRepository
from ..schemas.coverage import (
    CoverageByImmunizerItem,
    CoverageByImmunizerResponse,
    CoverageFilterOptions,
    CoverageHistoryPoint,
    CoverageHistoryResponse,
    CoverageHistorySeries,
    CoverageResponse,
    CoverageSummary,
    DeficitDistributionItem,
    MunicipalityRankingItem,
)

CRITICAL_CLASS = DEFICIT_LABELS[-1]


def classify_deficit(value: float | None) -> str | None:
    """Classe de risco a partir do déficit (mesmos limites das features de ML)."""
    if value is None:
        return None
    for upper, label in zip(DEFICIT_BINS[1:], DEFICIT_LABELS, strict=True):
        if value <= upper:
            return label
    return None


def unavailable_message(repo: CoverageRepository) -> str | None:
    if not repo.exists:
        return (
            "Dataset de features ausente. Execute o pipeline (python -m pipeline.cli) e "
            "'python -m ml.cli features'."
        )
    missing = repo.missing_columns()
    if missing:
        return f"Dataset de features sem as colunas: {missing}."
    return None


def round_value(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def history_point(row: dict[str, Any]) -> CoverageHistoryPoint:
    return CoverageHistoryPoint(
        year=row["year"],
        mean_coverage=round_value(row["mean_coverage"]),
        mean_deficit=round_value(row["mean_deficit"]),
        records=row["records"],
    )


class CoverageService:
    def __init__(self, repo: CoverageRepository) -> None:
        self.repo = repo

    def overview(self, flt: CoverageFilter, ranking_limit: int) -> CoverageResponse:
        message = unavailable_message(self.repo)
        if message:
            return CoverageResponse(status="data_unavailable", message=message)
        row = self.repo.summary(flt, CRITICAL_CLASS)
        summary = CoverageSummary(
            records=row["records"],
            municipalities=row["municipalities"],
            mean_coverage=round_value(row["mean_coverage"]),
            mean_deficit=round_value(row["mean_deficit"]),
            municipalities_below_target=row["below_target"],
            critical_municipalities=row["critical"],
        )
        counts = {r["deficit_class"]: r["count"] for r in self.repo.deficit_distribution(flt)}
        distribution = [
            DeficitDistributionItem(deficit_class=label, count=counts.pop(label))
            for label in DEFICIT_LABELS
            if label in counts
        ] + [DeficitDistributionItem(deficit_class=k, count=v) for k, v in sorted(counts.items())]
        _, ranking = self.repo.municipalities(flt, ranking_limit, 0, order_by_deficit=True)
        return CoverageResponse(
            status="ok",
            summary=summary,
            deficit_distribution=distribution,
            top_deficit_municipalities=[
                MunicipalityRankingItem(
                    municipality_code=r["municipality_code"],
                    municipality_name=r["municipality_name"],
                    mean_coverage=round_value(r["mean_coverage"]),
                    mean_deficit=round_value(r["mean_deficit"]),
                )
                for r in ranking
            ],
        )

    def filter_options(self) -> CoverageFilterOptions:
        message = unavailable_message(self.repo)
        if message:
            return CoverageFilterOptions(status="data_unavailable", message=message)
        options = self.repo.filter_options()
        classes = [c for c in DEFICIT_LABELS if c in options["deficit_classes"]]
        return CoverageFilterOptions(
            status="ok",
            years=options["years"],
            immunizers=options["immunizers"],
            deficit_classes=classes,
        )

    def by_immunizer(self, flt: CoverageFilter) -> CoverageByImmunizerResponse:
        message = unavailable_message(self.repo)
        if message:
            return CoverageByImmunizerResponse(status="data_unavailable", message=message)
        return CoverageByImmunizerResponse(
            status="ok",
            items=[
                CoverageByImmunizerItem(
                    immunizer=row["immunizer"],
                    mean_coverage=round_value(row["mean_coverage"]),
                    mean_deficit=round_value(row["mean_deficit"]),
                )
                for row in self.repo.by_immunizer(flt)
            ],
        )

    def history(self, flt: CoverageFilter) -> CoverageHistoryResponse:
        message = unavailable_message(self.repo)
        if message:
            return CoverageHistoryResponse(status="data_unavailable", message=message)
        if not flt.municipality_codes:
            rows = self.repo.history(flt, by_municipality=False)
            series = [
                CoverageHistorySeries(
                    key="all", label="Todos", points=[history_point(r) for r in rows]
                )
            ]
            return CoverageHistoryResponse(status="ok", series=series)

        rows = self.repo.history(flt, by_municipality=True)
        series = [
            CoverageHistorySeries(
                key=code,
                label=code,
                points=[history_point(r) for r in rows if r["municipality_code"] == code],
            )
            for code in flt.municipality_codes
        ]
        return CoverageHistoryResponse(status="ok", series=series)
