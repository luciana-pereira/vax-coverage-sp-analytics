"""Gera uma base agregada de demonstração a partir de dados sintéticos."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import duckdb
import pandas as pd

from backend.app.repositories.vaccination_analytics_repository import (
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_ROWS,
    csv_snapshot,
)


def init_db(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {source}")
    if destination.exists():
        raise FileExistsError(f"A base de destino já existe: {destination}")
    if source.suffix.lower() == ".csv":
        if source.stat().st_size > MAX_UPLOAD_BYTES:
            raise ValueError("O CSV excede o limite de 25 MiB.")
        content = source.read_bytes()
    elif source.suffix.lower() == ".parquet":
        with duckdb.connect(":memory:") as connection:
            frame = connection.execute(
                "SELECT * FROM read_parquet(?) LIMIT ?", [str(source), MAX_UPLOAD_ROWS + 1]
            ).fetchdf()
        if len(frame) > MAX_UPLOAD_ROWS:
            raise ValueError("O arquivo excede o limite de 500.000 linhas.")
        content = frame.to_csv(index=False).encode("utf-8")
    else:
        raise ValueError("A entrada deve ser um arquivo CSV ou Parquet.")
    snapshot = csv_snapshot(content)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp_dir:
        temp_path = Path(temp_dir) / "bootstrap.duckdb"
        with duckdb.connect(str(temp_path)) as connection:
            connection.register("incoming_groups", pd.DataFrame(snapshot.rows))
            connection.execute("CREATE TABLE analytics_groups AS SELECT * FROM incoming_groups")
            connection.execute("CREATE TABLE analytics_metadata (dimensions VARCHAR NOT NULL)")
            connection.execute(
                "INSERT INTO analytics_metadata VALUES (?)", [json.dumps(snapshot.dimensions)]
            )
        temp_path.rename(destination)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria uma base agregada de demonstração a partir de dados sintéticos."
    )
    parser.add_argument("--input", type=Path, required=True, help="CSV ou Parquet sintético")
    parser.add_argument("--output", type=Path, required=True, help="Caminho do novo DuckDB")
    args = parser.parse_args()
    init_db(args.input, args.output)
    print(f"Base sintética criada em {args.output.resolve()}")


if __name__ == "__main__":
    main()
