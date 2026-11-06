"""Acesso a dados Parquet via DuckDB (camada de persistência somente leitura)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

REQUIRED_COLUMNS = (
    "municipality_code",
    "year",
    "coverage",
    "deficit",
    "deficit_class",
    "immunizer",
)


@dataclass(frozen=True)
class CoverageFilter:
    year: int | None = None
    year_from: int | None = None
    year_to: int | None = None
    immunizer: str | None = None
    municipality_codes: list[str] = field(default_factory=list)
    deficit_class: str | None = None


class ParquetSource:
    """Arquivo Parquet consultado em memória pelo DuckDB."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @property
    def exists(self) -> bool:
        return self.path.is_file()

    @property
    def _from(self) -> str:
        escaped = self.path.as_posix().replace("'", "''")
        return f"read_parquet('{escaped}')"

    def columns(self) -> list[str]:
        if not self.exists:
            return []
        con = duckdb.connect(":memory:")
        try:
            rows = con.execute(f"DESCRIBE SELECT * FROM {self._from}").fetchall()
        finally:
            con.close()
        return [row[0] for row in rows]

    def rows(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        con = duckdb.connect(":memory:")
        try:
            cursor = con.execute(sql, params or [])
            names = [d[0] for d in cursor.description]
            return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
        finally:
            con.close()

    def frame(self, sql: str, params: list[Any] | None = None) -> pd.DataFrame:
        con = duckdb.connect(":memory:")
        try:
            return con.execute(sql, params or []).fetchdf()
        finally:
            con.close()


class CoverageRepository(ParquetSource):
    """Consultas agregadas sobre `features.parquet`."""

    def missing_columns(self) -> list[str]:
        present = set(self.columns())
        return [c for c in REQUIRED_COLUMNS if c not in present]

    def _name_expr(self) -> str:
        return (
            "any_value(municipality_name)"
            if "municipality_name" in self.columns()
            else "CAST(NULL AS VARCHAR)"
        )

    def _where(self, flt: CoverageFilter) -> tuple[str, list[Any]]:
        columns = set(self.columns())
        clauses: list[str] = []
        params: list[Any] = []
        if flt.year is not None:
            clauses.append("CAST(year AS INTEGER) = ?")
            params.append(flt.year)
        if flt.year_from is not None:
            clauses.append("CAST(year AS INTEGER) >= ?")
            params.append(flt.year_from)
        if flt.year_to is not None:
            clauses.append("CAST(year AS INTEGER) <= ?")
            params.append(flt.year_to)
        if flt.immunizer is not None:
            if "immunizer" in columns:
                clauses.append("CAST(immunizer AS VARCHAR) = ?")
                params.append(flt.immunizer)
            else:
                clauses.append("1 = 0")
        if flt.municipality_codes:
            marks = ", ".join("?" for _ in flt.municipality_codes)
            clauses.append(f"CAST(municipality_code AS VARCHAR) IN ({marks})")
            params.extend(flt.municipality_codes)
        if flt.deficit_class is not None:
            clauses.append("CAST(deficit_class AS VARCHAR) = ?")
            params.append(flt.deficit_class)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def filter_options(self) -> dict[str, list[Any]]:
        columns = set(self.columns())
        years = self.rows(
            f"SELECT DISTINCT CAST(year AS INTEGER) AS v FROM {self._from} "
            "WHERE year IS NOT NULL ORDER BY v"
        )
        classes = self.rows(
            f"SELECT DISTINCT CAST(deficit_class AS VARCHAR) AS v FROM {self._from} "
            "WHERE deficit_class IS NOT NULL"
        )
        immunizers = (
            self.rows(
                f"SELECT DISTINCT CAST(immunizer AS VARCHAR) AS v FROM {self._from} "
                "WHERE immunizer IS NOT NULL ORDER BY v"
            )
            if "immunizer" in columns
            else []
        )
        return {
            "years": [r["v"] for r in years],
            "immunizers": [r["v"] for r in immunizers],
            "deficit_classes": [r["v"] for r in classes],
        }

    def summary(self, flt: CoverageFilter, critical_class: str) -> dict[str, Any]:
        where, params = self._where(flt)
        sql = (
            "SELECT COUNT(*) AS records, "
            "COUNT(DISTINCT municipality_code) AS municipalities, "
            "AVG(coverage) AS mean_coverage, AVG(deficit) AS mean_deficit, "
            "COUNT(DISTINCT CASE WHEN deficit > 0 THEN municipality_code END) AS below_target, "
            "COUNT(DISTINCT CASE WHEN CAST(deficit_class AS VARCHAR) = ? "
            f"THEN municipality_code END) AS critical FROM {self._from}{where}"
        )
        return self.rows(sql, [critical_class, *params])[0]

    def deficit_distribution(self, flt: CoverageFilter) -> list[dict[str, Any]]:
        where, params = self._where(flt)
        extra = " AND deficit_class IS NOT NULL" if where else " WHERE deficit_class IS NOT NULL"
        sql = (
            "SELECT CAST(deficit_class AS VARCHAR) AS deficit_class, COUNT(*) AS count "
            f"FROM {self._from}{where}{extra} GROUP BY 1"
        )
        return self.rows(sql, params)

    def municipalities(
        self, flt: CoverageFilter, limit: int, offset: int, order_by_deficit: bool = False
    ) -> tuple[int, list[dict[str, Any]]]:
        where, params = self._where(flt)
        grouped = (
            "SELECT CAST(municipality_code AS VARCHAR) AS municipality_code, "
            f"{self._name_expr()} AS municipality_name, "
            "AVG(coverage) AS mean_coverage, AVG(deficit) AS mean_deficit, COUNT(*) AS records "
            f"FROM {self._from}{where} GROUP BY 1"
        )
        total = self.rows(f"SELECT COUNT(*) AS n FROM ({grouped})", params)[0]["n"]
        order = (
            "mean_deficit DESC NULLS LAST, municipality_code"
            if order_by_deficit
            else "municipality_name NULLS LAST, municipality_code"
        )
        items = self.rows(
            f"SELECT * FROM ({grouped}) ORDER BY {order} LIMIT ? OFFSET ?",
            [*params, limit, offset],
        )
        return int(total), items

    def history(self, flt: CoverageFilter, by_municipality: bool) -> list[dict[str, Any]]:
        where, params = self._where(flt)
        code = (
            "CAST(municipality_code AS VARCHAR) AS municipality_code, " if by_municipality else ""
        )
        group = "1, 2" if by_municipality else "1"
        sql = (
            f"SELECT CAST(year AS INTEGER) AS year, {code}"
            "AVG(coverage) AS mean_coverage, AVG(deficit) AS mean_deficit, COUNT(*) AS records "
            f"FROM {self._from}{where} GROUP BY {group} ORDER BY {group}"
        )
        return self.rows(sql, params)

    def by_immunizer(self, flt: CoverageFilter) -> list[dict[str, Any]]:
        if "immunizer" not in self.columns():
            return []
        where, params = self._where(flt)
        sql = (
            "SELECT CAST(immunizer AS VARCHAR) AS immunizer, AVG(coverage) AS mean_coverage, "
            f"AVG(deficit) AS mean_deficit FROM {self._from}{where} GROUP BY 1 ORDER BY 1"
        )
        return self.rows(sql, params)

    def quality(self) -> dict[str, Any]:
        columns = self.columns()
        null_exprs = ", ".join(
            f'COUNT(*) FILTER (WHERE "{c}" IS NULL) AS "n_{i}"' for i, c in enumerate(columns)
        )
        counts = self.rows(f"SELECT COUNT(*) AS rows, {null_exprs} FROM {self._from}")[0]
        distinct = self.rows(f"SELECT COUNT(*) AS n FROM (SELECT DISTINCT * FROM {self._from})")[0]
        extra = ""
        if "municipality_code" in columns:
            extra += ", COUNT(DISTINCT municipality_code) AS municipalities"
        if "year" in columns:
            extra += (
                ", MIN(CAST(year AS INTEGER)) AS year_min, "
                "MAX(CAST(year AS INTEGER)) AS year_max"
            )
        stats = self.rows(f"SELECT COUNT(*) AS n{extra} FROM {self._from}")[0]
        records_by_year = []
        if "year" in columns:
            records_by_year = self.rows(
                f"SELECT CAST(year AS INTEGER) AS year, COUNT(*) AS records "
                f"FROM {self._from} WHERE year IS NOT NULL GROUP BY 1 ORDER BY 1"
            )
        total = int(counts["rows"])
        return {
            "rows": total,
            "duplicate_rows": total - int(distinct["n"]),
            "municipalities": stats.get("municipalities"),
            "year_min": stats.get("year_min"),
            "year_max": stats.get("year_max"),
            "records_by_year": records_by_year,
            "columns": [
                {"name": c, "null_count": int(counts[f"n_{i}"])} for i, c in enumerate(columns)
            ],
        }


class PredictionRepository(ParquetSource):
    """Linhas do dataset de ML ainda sem rótulo (base da inferência)."""

    def latest_unlabeled(
        self,
        target_column: str,
        feature_columns: list[str],
        year: int | None,
        municipality_code: str | None,
        immunizer: str | None,
    ) -> pd.DataFrame:
        columns = set(self.columns())
        wanted = ("municipality_code", "municipality_name", "immunizer")
        extra_cols = [c for c in wanted if c in columns]
        select = ", ".join(f'"{c}"' for c in dict.fromkeys([*extra_cols, *feature_columns, "year"]))
        clauses = [f'"{target_column}" IS NULL']
        params: list[Any] = []
        if year is not None:
            clauses.append("CAST(year AS INTEGER) = ?")
            params.append(year)
        else:
            clauses.append(
                f'CAST(year AS INTEGER) = (SELECT MAX(CAST(year AS INTEGER)) FROM {self._from} '
                f'WHERE "{target_column}" IS NULL)'
            )
        if municipality_code is not None and "municipality_code" in columns:
            clauses.append("CAST(municipality_code AS VARCHAR) = ?")
            params.append(municipality_code)
        if immunizer is not None and "immunizer" in columns:
            clauses.append("CAST(immunizer AS VARCHAR) = ?")
            params.append(immunizer)
        sql = f"SELECT {select} FROM {self._from} WHERE {' AND '.join(clauses)}"
        return self.frame(sql, params)
