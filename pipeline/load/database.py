from pathlib import Path

import duckdb
import pandas as pd


def save_dataframe(df: pd.DataFrame, db_path: Path, table: str):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.register("incoming_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM incoming_df")
    finally:
        con.close()


def query(db_path: Path, sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()
