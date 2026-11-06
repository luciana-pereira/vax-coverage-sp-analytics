# Dicionário de dados

Esquema **canônico** produzido pelo pipeline e usado por ML, API e dashboard. Os nomes de colunas da fonte são mapeados para estes por `data/external/column_mapping.json`.

## Dataset processado (`data/processed/vaccination.parquet`)

| Campo | Significado | Origem | Regra |
|---|---|---|---|
| `municipality_code` | Código do município | SUS/IBGE | Chave de integração; obrigatório |
| `municipality_name` | Nome do município | SUS/IBGE | Opcional; nunca usar como chave |
| `immunizer` | Sigla do imunizante | PNI | Obrigatório; no raw local é `sg_imunobiologico`. `codigo_vacina` da API completa não é equivalente sem cruzamento oficial |
| `year` | Ano de referência | SUS | Inteiro; obrigatório |
| `doses` | Doses aplicadas | SUS | Numérico ≥ 0; somadas por chave na junção com a população |
| `population` | População-alvo | IBGE/estimativa apropriada | Numérico > 0; fornecida externamente |

## Dataset de features (`data/processed/features.parquet`)

Contém as colunas acima mais:

| Campo | Significado | Regra |
|---|---|---|
| `coverage` | Cobertura (%) | `doses / population × 100`; nulo se população = 0 |
| `coverage_target` | Meta (%) | Meta explicitamente configurada por imunizante; ML bloqueia quando a meta não está configurada |
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
| `data/external/target_population.csv` | `municipality_code, year, immunizer, population` (necessário para cobertura) |
| `data/external/coverage_targets.json` | `{"<imunizante>": <meta %>}` (necessário para gerar features/ML) |
| `data/external/sp_municipios.geojson` | GeoJSON `FeatureCollection` municipal (opcional, para o mapa) |
