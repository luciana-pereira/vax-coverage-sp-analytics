# Backend e pipeline de machine learning

Este documento descreve a implementação do servidor FastAPI, a ingestão de dados e o ciclo de treinamento e inferência do Vax Coverage SP Analytics. Os caminhos apresentados são os padrões relativos à raiz do repositório, salvo indicação contrária.

API de produção: [URL base](https://vax-coverage-sp-analytics.onrender.com/api/v1) · [Swagger UI](https://vax-coverage-sp-analytics.onrender.com/docs) · [ReDoc](https://vax-coverage-sp-analytics.onrender.com/redoc).

> **Precisão do contrato:** `GradientBoostingClassifier` é um dos candidatos, não necessariamente o modelo campeão. As classes implementadas são `baixo`, `moderado` e `alto`; `medio` e `critico` não são classes do pipeline atual. O endpoint de saúde verifica o serviço, não os artefatos.

## 1. Arquitetura do servidor

O frontend Angular acessa a API REST sob `/api/v1`. O backend usa routers FastAPI, schemas Pydantic, serviços e repositórios:

```text
Cliente Angular
    │ HTTP
    ▼
backend/app/main.py ── configuração, CORS, request ID e tratamento de erros
    │
    ▼
api/v1/ ── rotas e validação de parâmetros
    │ Depends
    ▼
services/ ── regras de negócio, agregação e inferência
    │
    ▼
repositories/ ── leitura de Parquet, JSONL e artefatos
    │
    ├── DuckDB em memória para consultar Parquet
    └── ml/inference para carregar o modelo e realizar predições
```

O servidor não executa treinamento. A produção dos arquivos processados e do modelo é responsabilidade das CLIs de `pipeline/` e `ml/`. O fluxo separado de analytics também aceita CSV e consulta a API PNI para gerar agregados temporários em memória.

### Estrutura de pastas

```text
backend/
  app/
    main.py             Aplicação FastAPI, middleware e handlers
    api/
      deps.py           Injeção de dependências dos serviços e repositórios
      v1/               Routers REST versionados
    core/               Configuração, logging e erros
    schemas/            Contratos Pydantic das requisições e respostas
    services/           Regras de negócio, relatórios e inferência
    repositories/       Acesso aos datasets e artefatos
  tests/                Testes da API e dos serviços
pipeline/
  cli.py                Comandos de extração, transformação, validação e carga
  extract/              Consulta paginada às fontes
  ingestion/            Processamento de entradas
  transform/            Normalização e integração da população-alvo
  validate/             Validação dos dados e denominadores
  load/                 Persistência e consultas DuckDB
ml/
  cli.py                Comandos de features, treino, avaliação e predição
  features/             Cobertura, déficit e dataset supervisionado
  models/               Modelos candidatos e pré-processamento
  training/             Treinamento e seleção temporal
  evaluation/           Cálculo e leitura de métricas
  inference/            Carregamento e aplicação do modelo persistido
```

A aplicação adiciona `X-Request-ID` às respostas para correlação com os logs. Erros de validação e internos são apresentados em um envelope com `detail` e `request_id`; erros internos são registrados no servidor e retornam mensagem sanitizada. A configuração de CORS utiliza `CORS_ORIGINS` e permite os métodos `GET`, `POST`, `PUT`, `DELETE` e `OPTIONS`, incluindo preflight.

### Serviços e repositórios

| Serviço | Responsabilidade |
|---|---|
| `CoverageService` | Indicadores, distribuição, ranking, filtros e histórico de cobertura e déficit. |
| `MunicipalityService` | Lista e detalhe de municípios. |
| `PredictionService` | Inferência para o ano seguinte usando os artefatos de ML. |
| `ModelService` | Exposição do relatório de avaliação. |
| `DataQualityService` | Estado dos artefatos, qualidade e lacunas dos dados. |
| `GeoService` | Disponibilização do GeoJSON configurado. |
| `VaccinationAnalyticsService` | Agregação de JSONL, CSV temporário ou PostgreSQL, distinguindo município do paciente e do estabelecimento. |

`CoverageRepository` consulta as features, `PredictionRepository` seleciona dados para inferência e `ArtifactRepository` acessa arquivos de artefatos.

## 2. Ingestão e armazenamento

```text
API PNI ── extract ──► data/raw/*.jsonl
                              │ transform + validação
                              ▼
                data/processed/vaccination.parquet
                       │                    │
                     load                features
                       ▼                    ▼
       data/processed/vax.duckdb   features.parquet + ml_dataset.parquet
                                            │ train
                                            ▼
                              modelo joblib + metrics.json
```

1. **Extração:** `pipeline.cli extract --year ANO` consulta o endpoint anual do PNI com `limit` e `offset` e grava JSONL, um objeto por linha, em `data/raw/`. Um arquivo temporário é substituído pelo resultado apenas após uma extração bem-sucedida.
2. **Transformação:** `transform` lê o JSONL configurado por `RAW_FILE_NAME`, deriva ano e doses quando possível, aplica filtro de UF quando presente e mapeia colunas para o esquema canônico. A população-alvo é associada por município, ano e imunizante.
3. **Validação:** o pipeline verifica as colunas obrigatórias (`municipality_code`, `immunizer`, `year`, `doses`, `population`), valores inválidos, duplicidades e alinhamento com o CSV de população-alvo. Falhas bloqueiam a atualização do Parquet ou da tabela DuckDB.
4. **Parquet e carga:** o resultado validado é salvo em `data/processed/vaccination.parquet`. O comando `load` grava ou substitui a tabela `vaccination` no banco local `data/processed/vax.duckdb`.
5. **Leitura pela API:** a API de cobertura e predições consulta diretamente `features.parquet` e `ml_dataset.parquet` com conexões DuckDB **em memória** e `read_parquet`; não depende da tabela do arquivo `vax.duckdb` para essas rotas. A API de analytics também pode agregar JSONL local ou, quando configurado, consultar PostgreSQL; o resultado é agregado antes de ser enviado ao cliente.

O arquivo de mapeamento e o CSV de população-alvo são insumos necessários à transformação. População municipal total não deve ser utilizada como substituto da população-alvo de cada imunizante. `DEDUPLICATE_RAW` deve refletir a existência de identificadores apropriados; linhas idênticas sem identificador de dose não são necessariamente duplicatas. Consulte [pipeline de dados](data/pipeline.md) e [fontes de dados](data/sources.md).

### Analytics e upload CSV

`POST /api/v1/analytics/upload` aceita CSV de até 25 MiB e 500.000 linhas, valida e agrega seu conteúdo em memória, sem gravar ou retornar registros individuais. `POST /api/v1/analytics/pni` também gera um snapshot agregado temporário. Os dois retornam `source_token`, que pode ser enviado a `GET /api/v1/analytics`; o cache é local ao processo, com validade de 30 minutos e até cinco snapshots. Um token expirado ou inexistente retorna HTTP 410. O upload **não** substitui o pipeline de cobertura nem treina o modelo.

## 3. Pipeline de machine learning

### Preparação e alvo

O comando `python -m ml.cli features` valida o Parquet processado, o alinhamento com `target_population.csv` e a presença de metas em `coverage_targets.json` para os imunizantes. Não produz features se os insumos exigidos estiverem ausentes ou inválidos.

- `coverage = doses / population × 100`.
- `deficit = max(0, coverage_target − coverage)`, em pontos percentuais.
- A classe do ano é calculada a partir do déficit:

| Classe | Déficit |
|---|---|
| `baixo` | Até 5 pontos percentuais, inclusive |
| `moderado` | Acima de 5 e até 15 pontos percentuais, inclusive |
| `alto` | Acima de 15 pontos percentuais |

O alvo `deficit_class_next` é a classe do **ano imediatamente seguinte** para o mesmo município e imunizante. Quando não há observação do ano seguinte, o alvo fica nulo e a linha pode ser usada para inferência. Os atributos do ano corrente e defasados incluem `coverage`, `deficit`, `doses`, `population`, `year`, `coverage_prev`, `deficit_prev`, `coverage_delta` e `immunizer`, quando presentes. A classe corrente e o próprio alvo não são usados como atributos, evitando prever a classe do mesmo ano a partir das variáveis que a definem.

### Modelos, treinamento e avaliação

O registro de candidatos compara:

| Nome no relatório | Estimador |
|---|---|
| `logistic_regression` | `LogisticRegression` |
| `random_forest` | `RandomForestClassifier` |
| `gradient_boosting` | `GradientBoostingClassifier` |

Cada candidato utiliza um pipeline scikit-learn com imputação e padronização das variáveis numéricas e imputação e one-hot encoding das categóricas. O campeão é escolhido pelo **F1 macro**; portanto, não há garantia de que o Gradient Boosting seja selecionado. `ML_RANDOM_STATE` controla a aleatoriedade dos candidatos que a utilizam.

O split é temporal e usa somente linhas com alvo conhecido:

- Com **três ou mais períodos rotulados**, anos anteriores servem para treino, o penúltimo para validação e o último para teste. O campeão é selecionado pela validação e seu pipeline final é treinado com os dados anteriores ao ano de teste.
- Com **dois períodos rotulados**, não há validação separada; o teste é usado para seleção, o que torna o resultado potencialmente otimista e é registrado em `selection.note`.
- Menos de dois períodos rotulados ou menos de duas classes distintas no treino impedem o treinamento. Um único ano de dados não é suficiente.

O relatório inclui accuracy, precision, recall e F1 em versões macro e ponderada, matriz de confusão (linhas reais e colunas previstas), baseline de persistência e importância das features quando disponível. As classes efetivamente presentes e a divisão temporal são registradas no relatório; não há métricas predefinidas ou resultados garantidos.

### Artefatos

| Caminho padrão | Conteúdo e consumidor |
|---|---|
| `data/processed/vaccination.parquet` | Dados canônicos validados; entrada da engenharia de atributos. |
| `data/processed/features.parquet` | Cobertura, déficit e classes; utilizado pela API de cobertura. |
| `data/processed/ml_dataset.parquet` | Features, defasagens e `deficit_class_next`; entrada do treino e da API de predições. |
| `data/models/vax_deficit_model.joblib` | Pipeline scikit-learn campeão, incluindo pré-processamento e estimador. |
| `data/models/metrics.json` | Alvo, atributos, classes, divisão, critério de seleção, modelos, métricas, baseline e importância das features. |

Os caminhos do modelo, métricas e datasets podem ser ajustados por `MODEL_PATH`, `METRICS_PATH`, `FEATURES_PATH` e `ML_DATASET_PATH`. O backend carrega o modelo com joblib e mantém cache associado ao caminho e à data de modificação. Para inferência, também necessita do relatório de métricas para recuperar a lista de atributos e o nome do campeão. Carregue apenas artefatos joblib de origem confiável.

### Execução das etapas

Na raiz, com o ambiente Python configurado e ativado:

```powershell
# Extração é opcional se o JSONL configurado já estiver disponível.
python -m pipeline.cli extract --year 2024
python -m pipeline.cli transform
python -m pipeline.cli validate
python -m pipeline.cli load
python -m ml.cli features
python -m ml.cli train
python -m ml.cli evaluate
python -m ml.cli predict
```

`load` exige Parquet e população-alvo válidos; `train` exige o dataset gerado por `features`. A extração do exemplo usa apenas um ano: é necessário fornecer uma série histórica suficiente antes de treinar. `predict` requer modelo, métricas e linhas sem rótulo. Consulte [detalhes do ML](ml/ml-pipeline.md).

## 4. Endpoints REST

Base local padrão: `http://localhost:8000/api/v1`. Os contratos completos e schemas são expostos em [Swagger UI](http://localhost:8000/docs), [ReDoc](http://localhost:8000/redoc) e [endpoints](api/endpoints.md).

### `GET /api/v1/models`

Retorna o relatório do último treinamento, não apenas as métricas do campeão. Não recebe parâmetros de consulta.

| Campo | Descrição |
|---|---|
| `status` | `ok` ou `not_trained`. |
| `message` | Mensagem explicativa, quando aplicável. |
| `generated_at`, `target`, `features`, `classes` | Metadados do treino. |
| `split`, `selection` | Partição temporal e critério de seleção. |
| `best_model` | Nome do modelo campeão. |
| `models` | Lista de candidatos com `name`, `is_best`, `validation` e `test`; cada conjunto de métricas inclui matriz de confusão. |
| `baseline`, `feature_importance` | Baseline de persistência e importância das features, quando disponíveis. |

O relatório ausente retorna HTTP 200 com `status: "not_trained"` e instrução para treinar. Erros internos, como relatório inválido, podem retornar HTTP 500 com envelope sanitizado. O endpoint lê `metrics.json` e não confirma, por si só, a existência ou integridade do arquivo joblib.

### `GET /api/v1/predictions`

Aplica o modelo às linhas de `ml_dataset.parquet` cujo `deficit_class_next` é nulo. Por padrão usa o último ano sem rótulo; `year` permite selecionar outro ano de origem. O ano previsto é `source_year + 1`.

| Parâmetro | Tipo | Padrão / regra |
|---|---|---|
| `year` | inteiro, opcional | Ano dos atributos; sem valor, usa o último ano sem rótulo. |
| `municipality_code` | string, opcional | Filtra pelo código do município, quando a coluna existe. |
| `immunizer` | string, opcional | Filtra pelo imunizante, quando a coluna existe. |
| `predicted_class` | string, opcional | Filtra a classe após inferência. |
| `limit` | inteiro | Padrão 100; entre 1 e 1000. |
| `offset` | inteiro | Padrão 0; não negativo. |

A resposta contém `status`, `message`, `model_name`, `source_year`, `target_year`, `total`, `class_distribution` e `items`. Cada item contém `municipality_code`, `municipality_name`, `immunizer`, `source_year`, `predicted_class` e `probabilities` por classe, quando disponíveis. A distribuição e o total refletem os filtros antes da paginação; itens são ordenados por código municipal e imunizante.

O retorno HTTP 200 pode trazer `model_unavailable`, `data_unavailable` ou `ok` com lista vazia e mensagem quando não há linhas elegíveis. Um parâmetro inválido retorna HTTP 422; falhas internas retornam HTTP 500. As classes dependem do modelo treinado; não se deve interpretar um rótulo não implementado como parte do contrato.

### `GET /api/v1/health`

Não recebe parâmetros e retorna HTTP 200 com:

```json
{
  "status": "ok",
  "app": "Vax Coverage SP Analytics API",
  "version": "0.1.0",
  "environment": "development"
}
```

O valor de `environment` depende de `APP_ENV`. Este endpoint confirma que a aplicação responde; **não testa banco, datasets, modelo ou métricas**. Para inspecionar existência dos artefatos, qualidade das features e lacunas conhecidas, use `GET /api/v1/data-quality`. A existência de um arquivo, por si só, não garante que seu conteúdo seja válido ou que o modelo esteja pronto para inferência.

### Exemplos PowerShell

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
Invoke-RestMethod http://localhost:8000/api/v1/data-quality
Invoke-RestMethod http://localhost:8000/api/v1/models
Invoke-RestMethod 'http://localhost:8000/api/v1/predictions?limit=20&offset=0'
```

## 5. Configuração e operação

Copie `.env.example` para `.env` se ainda não existir. Variáveis relevantes incluem `DATA_DIR`, `RAW_FILE_NAME`, `COLUMN_MAPPING_PATH`, `TARGET_POPULATION_PATH`, `COVERAGE_TARGETS_PATH`, `DUCKDB_PATH`, `FEATURES_PATH`, `ML_DATASET_PATH`, `MODEL_PATH`, `METRICS_PATH`, `GEOJSON_PATH`, `GEOJSON_CODE_PROPERTY`, `CORS_ORIGINS`, `APP_ENV`, `LOG_LEVEL` e `ML_RANDOM_STATE`. Fontes PostgreSQL opcionais usam `VACCINATION_DATABASE_URL`, `AIVEN_DATABASE_URL` ou `DATABASE_URL` e `VACCINATION_TABLE`; a conexão exige SSL. Não versione credenciais nem `.env`.

Para iniciar a API em desenvolvimento a partir da raiz:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD;$PWD\backend"
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Para executar os testes do backend e regenerar a documentação OpenAPI após alterar contratos:

```powershell
python -m pytest backend/tests
python scripts/export_openapi.py
```

Veja também a [visão de arquitetura](architecture/overview.md), o [contrato da API](api/endpoints.md) e o [README principal](../README.md).

### Artefatos de dados

A API consulta os arquivos Parquet de features e ML com DuckDB em memória; `vax.duckdb` é produzido pelo pipeline, mas não substitui esses arquivos nas rotas. População-alvo, metas e outros arquivos de `external/` também são necessários para reproduzir o pipeline e o treinamento. Use apenas arquivos de modelo confiáveis e verifique os caminhos e estados em `/api/v1/data-quality`, `/api/v1/coverage` e `/api/v1/predictions`.
