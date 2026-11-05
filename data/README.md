# data/

Dados locais do projeto. O conteúdo **não é versionado** (apenas os `.gitkeep`).

| Pasta | Conteúdo |
|---|---|
| `raw/` | Registros brutos extraídos da fonte (JSONL) |
| `processed/` | `vaccination.parquet`, `features.parquet`, `ml_dataset.parquet`, `vax.duckdb` |
| `external/` | Arquivos fornecidos pelo grupo: `column_mapping.json`, `target_population.csv`, `coverage_targets.json`, GeoJSON municipal |
| `models/` | Artefatos gerados: modelo `.joblib` e `metrics.json` |

Formatos e origem: [docs/data](../docs/data/data_dictionary.md).
