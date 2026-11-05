import pandas as pd

from pipeline.load.database import query, save_dataframe


def test_save_and_query_roundtrip(tmp_path):
    db = tmp_path / "nested" / "vax.duckdb"
    df = pd.DataFrame({"municipality_code": ["1", "2"], "doses": [3, 4]})
    save_dataframe(df, db, "vaccination")
    out = query(db, "SELECT SUM(doses) AS total FROM vaccination")
    assert int(out.loc[0, "total"]) == 7


def test_save_dataframe_replaces_table(tmp_path):
    db = tmp_path / "vax.duckdb"
    save_dataframe(pd.DataFrame({"a": [1, 2]}), db, "t")
    save_dataframe(pd.DataFrame({"a": [9]}), db, "t")
    assert len(query(db, "SELECT * FROM t")) == 1
