# Endpoints da API

> Gerado por `python scripts/export_openapi.py` a partir de `openapi.json`. Não edite à mão: altere os schemas/routers e regenere.

**Vax Coverage SP Analytics API** — versão 0.1.0

Swagger UI: `/docs` · ReDoc: `/redoc` · Contrato: `/openapi.json`.

## Endpoints

| Método | Caminho | Resumo |
|---|---|---|
| GET | `/api/v1/health` | Verifica o estado da API |
| GET | `/api/v1/analytics` | Doses agregadas por período e dimensões |
| POST | `/api/v1/analytics/pni` | Atualizar agregados pela API PNI configurada |
| POST | `/api/v1/analytics/upload` | Validar e agregar CSV de vacinação |
| GET | `/api/v1/coverage` | Indicadores de cobertura e déficit |
| GET | `/api/v1/coverage/filters` | Valores disponíveis para os filtros |
| GET | `/api/v1/coverage/immunizers` | Cobertura e déficit por imunizante |
| GET | `/api/v1/coverage/history` | Série histórica de cobertura e déficit |
| GET | `/api/v1/municipalities` | Lista municípios com cobertura e déficit médios |
| GET | `/api/v1/municipalities/{municipality_id}` | Detalhe de um município |
| GET | `/api/v1/predictions` | Classe de déficit prevista para o ano seguinte |
| GET | `/api/v1/models` | Avaliação dos modelos treinados |
| GET | `/api/v1/data-quality` | Qualidade dos dados e lacunas conhecidas |
| GET | `/api/v1/geo/municipalities` | GeoJSON dos municípios de São Paulo |

### GET `/api/v1/health`

Retorna `ok` quando o serviço está em execução. Não consulta os dados.

| Código | Corpo |
|---|---|
| 200 | HealthResponse |
| 500 | ErrorResponse |

### GET `/api/v1/analytics`

Retorna agregados mensais, por sexo, faixa etária, vacina e município. Município do paciente e município do estabelecimento permanecem separados. Identificadores pessoais e linhas individuais nunca são retornados.

| Parâmetro | Em | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `year` | query | integer \| null | não |  |
| `vaccine` | query | string \| null | não |  |
| `age_group` | query | `0-4` \| `60+` \| null | não |  |
| `municipality_code` | query | string \| null | não |  |
| `municipality_basis` | query | `patient` \| `application` | não |  |
| `source_token` | query | string \| null | não |  |

| Código | Corpo |
|---|---|
| 200 | VaccinationAnalyticsResponse |
| 404 | ErrorResponse |
| 410 | A sessão de CSV expirou. |
| 422 | HTTPValidationError |

### POST `/api/v1/analytics/pni`

Consulta páginas da API PNI e agrega no backend. Os registros individuais da resposta, incluindo IDs, nunca são gravados nem retornados. A operação pode ser demorada.

| Parâmetro | Em | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `year` | query | integer | não |  |

| Código | Corpo |
|---|---|
| 200 | AnalyticsUploadResponse |
| 502 | A fonte PNI está indisponível ou retornou dados inválidos. |
| 422 | HTTPValidationError |

### POST `/api/v1/analytics/upload`

Aceita CSV de até 25 MiB e 500.000 linhas, agrega em memória e retorna somente contagens. O conteúdo individual não é gravado nem enviado ao frontend.

| Código | Corpo |
|---|---|
| 200 | AnalyticsUploadResponse |
| 413 | CSV excede o limite. |
| 415 | Tipo de conteúdo inválido. |
| 422 | Nome, schema, encoding ou conteúdo inválido. |

### GET `/api/v1/coverage`

KPIs agregados (cobertura média, déficit médio, municípios abaixo da meta e críticos), distribuição por classe de déficit e ranking de municípios com maior déficit médio. Médias simples sobre as linhas filtradas. Sem dataset, retorna `data_unavailable`.

| Parâmetro | Em | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `ranking_limit` | query | integer | não | Itens do ranking. |
| `year` | query | integer \| null | não | Ano exato. |
| `year_from` | query | integer \| null | não | Ano inicial. |
| `year_to` | query | integer \| null | não | Ano final. |
| `immunizer` | query | string \| null | não | Imunizante. |
| `municipality_code` | query | list[string] \| null | não | Código(s) do município; repita o parâmetro. |
| `deficit_class` | query | string \| null | não | Classe de déficit das linhas (baixo/moderado/alto). |

| Código | Corpo |
|---|---|
| 200 | CoverageResponse |
| 500 | ErrorResponse |
| 422 | ErrorResponse |

### GET `/api/v1/coverage/filters`

Anos, imunizantes (se a coluna existir) e classes de déficit presentes nos dados.

| Código | Corpo |
|---|---|
| 200 | CoverageFilterOptions |
| 500 | ErrorResponse |
| 422 | ErrorResponse |

### GET `/api/v1/coverage/immunizers`

Agrega cobertura e déficit médios por imunizante usando os filtros aplicados. Sem dimensões vacinais ou dataset válido, retorna `data_unavailable`.

| Parâmetro | Em | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `year` | query | integer \| null | não | Ano exato. |
| `year_from` | query | integer \| null | não | Ano inicial. |
| `year_to` | query | integer \| null | não | Ano final. |
| `immunizer` | query | string \| null | não | Imunizante. |
| `municipality_code` | query | list[string] \| null | não | Código(s) do município; repita o parâmetro. |
| `deficit_class` | query | string \| null | não | Classe de déficit das linhas (baixo/moderado/alto). |

| Código | Corpo |
|---|---|
| 200 | CoverageByImmunizerResponse |
| 500 | ErrorResponse |
| 422 | ErrorResponse |

### GET `/api/v1/coverage/history`

Evolução anual. Sem `municipality_code`, uma série agregada (`all`). Com um ou mais `municipality_code`, uma série por município (comparação).

| Parâmetro | Em | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `year` | query | integer \| null | não | Ano exato. |
| `year_from` | query | integer \| null | não | Ano inicial. |
| `year_to` | query | integer \| null | não | Ano final. |
| `immunizer` | query | string \| null | não | Imunizante. |
| `municipality_code` | query | list[string] \| null | não | Código(s) do município; repita o parâmetro. |
| `deficit_class` | query | string \| null | não | Classe de déficit das linhas (baixo/moderado/alto). |

| Código | Corpo |
|---|---|
| 200 | CoverageHistoryResponse |
| 500 | ErrorResponse |
| 422 | ErrorResponse |

### GET `/api/v1/municipalities`

Agregação por município sobre as linhas filtradas, ordenada por nome/código. Usada pelo mapa e pelo ranking. Sem dataset, retorna `data_unavailable`.

| Parâmetro | Em | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `limit` | query | integer | não |  |
| `offset` | query | integer | não |  |
| `year` | query | integer \| null | não | Ano exato. |
| `year_from` | query | integer \| null | não | Ano inicial. |
| `year_to` | query | integer \| null | não | Ano final. |
| `immunizer` | query | string \| null | não | Imunizante. |
| `municipality_code` | query | list[string] \| null | não | Código(s) do município; repita o parâmetro. |
| `deficit_class` | query | string \| null | não | Classe de déficit das linhas (baixo/moderado/alto). |

| Código | Corpo |
|---|---|
| 200 | MunicipalityListResponse |
| 500 | ErrorResponse |
| 422 | ErrorResponse |

### GET `/api/v1/municipalities/{municipality_id}`

Indicadores, histórico anual e resumo por imunizante do município (código).

| Parâmetro | Em | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `municipality_id` | path | string | sim |  |
| `year` | query | integer \| null | não | Ano exato. |
| `year_from` | query | integer \| null | não | Ano inicial. |
| `year_to` | query | integer \| null | não | Ano final. |
| `immunizer` | query | string \| null | não | Imunizante. |
| `municipality_code` | query | list[string] \| null | não | Código(s) do município; repita o parâmetro. |
| `deficit_class` | query | string \| null | não | Classe de déficit das linhas (baixo/moderado/alto). |

| Código | Corpo |
|---|---|
| 200 | MunicipalityDetailResponse |
| 500 | ErrorResponse |
| 422 | ErrorResponse |
| 404 | ErrorResponse |

### GET `/api/v1/predictions`

Aplica o modelo treinado aos atributos do último ano sem rótulo (ou de `year`). `status` indica `model_unavailable` ou `data_unavailable` quando faltam artefatos.

| Parâmetro | Em | Tipo | Obrigatório | Descrição |
|---|---|---|---|---|
| `year` | query | integer \| null | não | Ano dos atributos (origem). |
| `municipality_code` | query | string \| null | não |  |
| `immunizer` | query | string \| null | não |  |
| `predicted_class` | query | string \| null | não | Filtra pela classe prevista. |
| `limit` | query | integer | não |  |
| `offset` | query | integer | não |  |

| Código | Corpo |
|---|---|
| 200 | PredictionResponse |
| 500 | ErrorResponse |
| 422 | ErrorResponse |

### GET `/api/v1/models`

Relatório do último treino: alvo, atributos, divisão temporal, métricas por modelo (F1, precision, recall, matriz de confusão), baseline e importância das features. Retorna `not_trained` se o treino ainda não foi executado.

| Código | Corpo |
|---|---|
| 200 | ModelResponse |
| 500 | ErrorResponse |

### GET `/api/v1/data-quality`

Status dos artefatos (bruto, processado, features, modelo, GeoJSON, população-alvo), qualidade do dataset de features (nulos, duplicatas, anos) e dependências pendentes.

| Código | Corpo |
|---|---|
| 200 | DataQualityResponse |
| 500 | ErrorResponse |

### GET `/api/v1/geo/municipalities`

Entrega o GeoJSON configurado em `GEOJSON_PATH`. O projeto não inclui geometrias: sem o arquivo, retorna `data_unavailable`.

| Código | Corpo |
|---|---|
| 200 | GeoResponse |
| 500 | ErrorResponse |

## Schemas

### AnalyticsCategory

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `key` | string | sim |  |
| `label` | string | sim |  |
| `doses` | integer | sim |  |

### AnalyticsFilters

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `years` | list[integer] | não |  |
| `vaccines` | list[AnalyticsVaccineFilter] | não |  |
| `age_groups` | list[string] | não |  |
| `patient_municipalities` | list[AnalyticsMunicipalityFilter] | não |  |
| `application_municipalities` | list[AnalyticsMunicipalityFilter] | não |  |

### AnalyticsMonth

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `month` | string | sim |  |
| `doses` | integer | sim |  |

### AnalyticsMunicipalityCount

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `code` | string | sim |  |
| `name` | string \| null | não |  |
| `doses` | integer | sim |  |

### AnalyticsMunicipalityFilter

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `code` | string | sim |  |
| `name` | string \| null | não |  |

### AnalyticsUploadResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `message` | string \| null | não |  |
| `source` | string \| null | não |  |
| `source_updated_at` | string \| null | não |  |
| `generated_at` | string | sim |  |
| `year` | integer \| null | não |  |
| `period_start` | string \| null | não |  |
| `period_end` | string \| null | não |  |
| `total_doses` | integer | não |  |
| `statewide` | boolean | não |  |
| `dimensions` | dict[str, boolean] | não |  |
| `filters` | AnalyticsFilters | não |  |
| `monthly` | list[AnalyticsMonth] | não |  |
| `by_sex` | list[AnalyticsCategory] | não |  |
| `by_age_group` | list[AnalyticsCategory] | não |  |
| `by_vaccine` | list[AnalyticsVaccineCount] | não |  |
| `by_patient_municipality` | list[AnalyticsMunicipalityCount] | não |  |
| `by_application_municipality` | list[AnalyticsMunicipalityCount] | não |  |
| `warnings` | list[string] | não |  |
| `accepted_rows` | integer | não |  |
| `source_token` | string \| null | não |  |

### AnalyticsVaccineCount

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `key` | string | sim |  |
| `code` | string \| null | não |  |
| `abbreviation` | string \| null | não |  |
| `description` | string \| null | não |  |
| `label` | string | sim |  |
| `doses` | integer | sim |  |

### AnalyticsVaccineFilter

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `key` | string | sim |  |
| `code` | string \| null | não |  |
| `abbreviation` | string \| null | não |  |
| `description` | string \| null | não |  |
| `label` | string | sim |  |

### ArtifactStatus

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `name` | string | sim |  |
| `description` | string | sim |  |
| `path` | string | sim | Caminho relativo à raiz do projeto. |
| `exists` | boolean | sim |  |
| `size_bytes` | integer \| null | não |  |

### BaselineInfo

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `description` | string | sim |  |
| `test` | ModelMetrics | sim |  |

### ColumnQuality

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `name` | string | sim |  |
| `null_count` | integer | sim |  |
| `null_ratio` | number | sim |  |

### CoverageByImmunizerItem

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `immunizer` | string | sim |  |
| `mean_coverage` | number \| null | sim |  |
| `mean_deficit` | number \| null | sim |  |

### CoverageByImmunizerResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `message` | string \| null | não |  |
| `items` | list[CoverageByImmunizerItem] | não |  |

### CoverageFilterOptions

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `message` | string \| null | não |  |
| `years` | list[integer] | não |  |
| `immunizers` | list[string] | não |  |
| `deficit_classes` | list[string] | não |  |

### CoverageHistoryPoint

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `year` | integer | sim |  |
| `mean_coverage` | number \| null | sim |  |
| `mean_deficit` | number \| null | sim |  |
| `records` | integer | sim |  |

### CoverageHistoryResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `message` | string \| null | não |  |
| `series` | list[CoverageHistorySeries] | não |  |

### CoverageHistorySeries

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `key` | string | sim | 'all' ou o código do município. |
| `label` | string | sim |  |
| `points` | list[CoverageHistoryPoint] | sim |  |

### CoverageResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `message` | string \| null | não | Motivo quando não há dados. |
| `summary` | CoverageSummary \| null | não |  |
| `deficit_distribution` | list[DeficitDistributionItem] | não |  |
| `top_deficit_municipalities` | list[MunicipalityRankingItem] | não |  |

### CoverageSummary

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `records` | integer | sim | Linhas (município x imunizante x ano) consideradas. |
| `municipalities` | integer | sim | Municípios distintos analisados. |
| `mean_coverage` | number \| null | sim | Cobertura média (%) das linhas filtradas. |
| `mean_deficit` | number \| null | sim | Déficit médio (p.p.) das linhas filtradas. |
| `municipalities_below_target` | integer | sim | Municípios com déficit > 0. |
| `critical_municipalities` | integer | sim | Municípios com classe de déficit 'alto'. |

### DataQualityResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `artifacts` | list[ArtifactStatus] | sim |  |
| `dataset` | DatasetQuality \| null | não |  |
| `known_gaps` | list[string] | sim | Dependências ainda não atendidas. |

### DatasetQuality

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `rows` | integer | sim |  |
| `municipalities` | integer \| null | não |  |
| `year_min` | integer \| null | não |  |
| `year_max` | integer \| null | não |  |
| `duplicate_rows` | integer | sim |  |
| `missing_columns` | list[string] | sim | Colunas esperadas ausentes. |
| `columns` | list[ColumnQuality] | sim |  |
| `records_by_year` | list[YearRecordCount] | não |  |

### DeficitDistributionItem

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `deficit_class` | string | sim |  |
| `count` | integer | sim |  |

### ErrorResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `detail` | string | sim | Descrição do erro. |
| `request_id` | string | sim | Identificador para correlacionar com o log do servidor. |

### FeatureImportanceItem

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `feature` | string | sim |  |
| `importance` | number | sim |  |

### GeoResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `message` | string \| null | não |  |
| `code_property` | string \| null | não | Propriedade do GeoJSON com o código do município. |
| `feature_count` | integer | não |  |
| `geojson` | dict[str, any] \| null | não | FeatureCollection GeoJSON. |

### HealthResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | string | sim | Estado do serviço. |
| `app` | string | sim | Nome da aplicação. |
| `version` | string | sim | Versão da API. |
| `environment` | string | sim | Ambiente de execução. |

### ImmunizerSummary

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `immunizer` | string | sim |  |
| `mean_coverage` | number \| null | sim |  |
| `mean_deficit` | number \| null | sim |  |

### ModelEntry

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `name` | string | sim |  |
| `is_best` | boolean | sim |  |
| `validation` | ModelMetrics \| null | não |  |
| `test` | ModelMetrics | sim |  |

### ModelMetrics

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `accuracy` | number | sim |  |
| `precision_macro` | number | sim |  |
| `precision_weighted` | number | sim |  |
| `recall_macro` | number | sim |  |
| `recall_weighted` | number | sim |  |
| `f1_macro` | number | sim |  |
| `f1_weighted` | number | sim |  |
| `confusion_matrix` | list[list[integer]] | sim | Linhas = real, colunas = previsto. |

### ModelResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `not_trained` | sim |  |
| `message` | string \| null | não |  |
| `generated_at` | string \| null | não |  |
| `target` | string \| null | não |  |
| `features` | list[string] | não |  |
| `classes` | list[string] | não |  |
| `split` | SplitInfo \| null | não |  |
| `selection` | SelectionInfo \| null | não |  |
| `best_model` | string \| null | não |  |
| `models` | list[ModelEntry] | não |  |
| `baseline` | BaselineInfo \| null | não |  |
| `feature_importance` | list[FeatureImportanceItem] | não |  |

### MunicipalityDetailResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `municipality` | MunicipalityItem | sim |  |
| `history` | list[CoverageHistoryPoint] | sim |  |
| `by_immunizer` | list[ImmunizerSummary] | não |  |

### MunicipalityItem

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `municipality_code` | string | sim |  |
| `municipality_name` | string \| null | não |  |
| `mean_coverage` | number \| null | sim |  |
| `mean_deficit` | number \| null | sim |  |
| `deficit_class` | string \| null | não | Classe calculada sobre o déficit médio. |
| `records` | integer | sim |  |

### MunicipalityListResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `message` | string \| null | não |  |
| `total` | integer | não |  |
| `limit` | integer | sim |  |
| `offset` | integer | sim |  |
| `items` | list[MunicipalityItem] | não |  |

### MunicipalityRankingItem

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `municipality_code` | string | sim |  |
| `municipality_name` | string \| null | não |  |
| `mean_coverage` | number \| null | sim |  |
| `mean_deficit` | number \| null | sim |  |

### PredictionItem

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `municipality_code` | string | sim |  |
| `municipality_name` | string \| null | não |  |
| `immunizer` | string \| null | não |  |
| `source_year` | integer | sim | Ano dos atributos usados na predição. |
| `predicted_class` | string | sim | Classe de déficit prevista para o ano seguinte. |
| `probabilities` | dict[str, number] \| null | não | Probabilidade por classe, se o modelo as fornece. |

### PredictionResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `model_unavailable` \| `data_unavailable` | sim |  |
| `message` | string \| null | não |  |
| `model_name` | string \| null | não |  |
| `source_year` | integer \| null | não |  |
| `target_year` | integer \| null | não |  |
| `total` | integer | não |  |
| `class_distribution` | dict[str, integer] | não |  |
| `items` | list[PredictionItem] | não |  |

### SelectionInfo

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `criterion` | string | sim |  |
| `split` | string | sim |  |
| `note` | string \| null | não |  |

### SplitInfo

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `scheme` | string | sim |  |
| `train_years` | list[integer] | sim |  |
| `validation_year` | integer \| null | não |  |
| `test_year` | integer | sim |  |
| `n_train` | integer | sim |  |
| `n_validation` | integer | sim |  |
| `n_test` | integer | sim |  |

### VaccinationAnalyticsResponse

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `status` | `ok` \| `data_unavailable` | sim |  |
| `message` | string \| null | não |  |
| `source` | string \| null | não |  |
| `source_updated_at` | string \| null | não |  |
| `generated_at` | string | sim |  |
| `year` | integer \| null | não |  |
| `period_start` | string \| null | não |  |
| `period_end` | string \| null | não |  |
| `total_doses` | integer | não |  |
| `statewide` | boolean | não |  |
| `dimensions` | dict[str, boolean] | não |  |
| `filters` | AnalyticsFilters | não |  |
| `monthly` | list[AnalyticsMonth] | não |  |
| `by_sex` | list[AnalyticsCategory] | não |  |
| `by_age_group` | list[AnalyticsCategory] | não |  |
| `by_vaccine` | list[AnalyticsVaccineCount] | não |  |
| `by_patient_municipality` | list[AnalyticsMunicipalityCount] | não |  |
| `by_application_municipality` | list[AnalyticsMunicipalityCount] | não |  |
| `warnings` | list[string] | não |  |

### YearRecordCount

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `year` | integer | sim |  |
| `records` | integer | sim |  |
