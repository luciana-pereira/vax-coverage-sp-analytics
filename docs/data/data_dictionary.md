# Dicionário de dados

Esquema **canônico** produzido pelo pipeline e usado por ML, API e dashboard. Os nomes de colunas da fonte são mapeados para estes por `data/external/column_mapping.json`.

## Dataset processado (`data/processed/vaccination.parquet`)

| Campo | Significado | Origem | Regra |
|---|---|---|---|
| `municipality_code` | Código do município | SUS/IBGE | Chave de integração; obrigatório |
| `municipality_name` | Nome do município | SUS/IBGE | Opcional; nunca usar como chave |
| `immunizer` | Código/nome do imunizante | SUS | Obrigatório para a API de cobertura; `codigo_vacina` permanece código bruto até haver cruzamento oficial |
| `year` | Ano de referência | SUS | Inteiro; obrigatório |
| `doses` | Doses aplicadas | SUS | Numérico ≥ 0; somadas por chave na junção com a população |
| `population` | População-alvo | IBGE/estimativa apropriada | Numérico > 0; fornecida externamente |

## Dataset de features (`data/processed/features.parquet`)

Contém as colunas acima mais:

| Campo | Significado | Regra |
|---|---|---|
| `coverage` | Cobertura (%) | `doses / population × 100`; nulo se população = 0 |
| `coverage_target` | Meta (%) | Meta padrão (`COVERAGE_TARGET_DEFAULT`) ou meta do imunizante |
| `deficit` | Déficit (p.p.) | `max(0, coverage_target − coverage)` |
| `deficit_class` | Classe | `baixo` ≤ 5, `moderado` ≤ 15, `alto` > 15 |

## Dataset de ML (`data/processed/ml_dataset.parquet`)

Features mais:

| Campo | Significado |
|---|---|
| `deficit_class_next` | **Alvo**: classe de déficit do ano seguinte (nulo no último ano: usado na inferência) |
| `coverage_prev`, `deficit_prev` | Valores do ano anterior (nulos se não houver) |
| `coverage_delta` | `coverage − coverage_prev` |

## Arquivos externos (fornecidos pelo grupo)

| Arquivo | Formato |
|---|---|
| `data/external/column_mapping.json` | `{"<coluna canônica>": "<coluna da fonte>"}` |
| `data/external/target_population.csv` | `municipality_code, year, [immunizer], population` |
| `data/external/coverage_targets.json` | `{"<imunizante>": <meta %>}` (opcional) |
| `data/external/sp_municipios.geojson` | GeoJSON `FeatureCollection` municipal (opcional, para o mapa) |
