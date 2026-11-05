import json
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/processed/features.parquet"
METRICS = ROOT / "data/models/metrics.json"

st.set_page_config(page_title="Vax Coverage SP", layout="wide")
st.title("💉 Vax Coverage SP Analytics")
st.caption("Análise de déficit de cobertura vacinal — Projeto Integrador IV")

if not FEATURES.exists():
    st.warning("Execute primeiro o pipeline de features.")
    st.stop()

df = pd.read_parquet(FEATURES)

st.sidebar.header("Filtros")
if "year" in df.columns:
    years = sorted(pd.to_numeric(df["year"], errors="coerce").dropna().unique())
    if years:
        year = st.sidebar.selectbox("Ano", years, index=len(years)-1)
        df = df[pd.to_numeric(df["year"], errors="coerce") == year]

if "deficit_class" in df.columns:
    classes = st.sidebar.multiselect(
        "Faixa de déficit",
        options=df["deficit_class"].dropna().unique().tolist(),
        default=df["deficit_class"].dropna().unique().tolist(),
    )
    df = df[df["deficit_class"].isin(classes)]

c1, c2, c3 = st.columns(3)
c1.metric("Registros", len(df))
c2.metric("Déficit médio", f"{df['deficit'].mean():.2f} p.p." if "deficit" in df else "—")
c3.metric("Cobertura média", f"{df['coverage'].mean():.2f}%" if "coverage" in df else "—")

st.subheader("Ranking de maior déficit")
if {"deficit"}.issubset(df.columns):
    display_cols = [c for c in ["municipality_name", "municipality_code", "immunizer", "municipio", "nome_municipio", "imunizante", "year", "coverage", "deficit", "deficit_class"] if c in df.columns]
    st.dataframe(df.sort_values("deficit", ascending=False)[display_cols].head(20), use_container_width=True)

st.subheader("Série histórica")
if {"year", "deficit"}.issubset(df.columns):
    chart = df.groupby("year", as_index=True)["deficit"].mean()
    st.line_chart(chart)

st.subheader("Desempenho dos modelos")
if METRICS.exists():
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    st.json(metrics)
