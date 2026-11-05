# Backend (FastAPI)

API REST que serve o dashboard. Não treina modelos e não escreve dados: lê os artefatos produzidos por `pipeline/` e `ml/`.

## Arquitetura

```text
app/
  main.py            criação do app, CORS, handler de erros
  core/              config (variáveis de ambiente), logging, errors
  api/deps.py        composição de repositories/services (injeção de dependências)
  api/v1/            routers finos: health, coverage, municipalities, predictions, models, data_quality, geo
  schemas/           contratos Pydantic (fonte de verdade do OpenAPI)
  services/          regras de negócio
  repositories/      acesso a Parquet via DuckDB e a artefatos em disco
tests/               testes do backend
```

Fluxo: router → service → repository. O `PredictionService` usa `ml.inference` para aplicar o modelo.

## Execução

Na raiz do repositório, com o `.venv` criado (`scripts/bootstrap`):

```powershell
$env:PYTHONPATH = "$PWD;$PWD\backend"
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

Ou `scripts/run.ps1 -Backend` / `scripts/run.sh --backend`. A API sobe em `http://localhost:8000`.

## Dependências

`backend/requirements.txt`: `fastapi`, `uvicorn` (servidor), `duckdb` (leitura de Parquet), `pandas` (resultado das consultas), `scikit-learn` e `joblib` (carregar o modelo na inferência), `numpy`, `python-dotenv`.

## Endpoints

Todos `GET` sob `/api/v1`: `health`, `coverage`, `coverage/filters`, `coverage/history`, `municipalities`, `municipalities/{municipality_id}`, `predictions`, `models`, `data-quality` e `geo/municipalities`. Referência completa em [docs/api/endpoints.md](../docs/api/endpoints.md).

## OpenAPI

`/docs` (Swagger UI), `/redoc` e `/openapi.json`. Após mudar rotas ou schemas: `python scripts/export_openapi.py`.

## Services, repositories e schemas

| Service | Responsabilidade |
|---|---|
| `CoverageService` | KPIs, distribuição, ranking, histórico e filtros; classifica o déficit médio |
| `MunicipalityService` | Lista e detalhe de municípios |
| `PredictionService` | Previsão do ano seguinte com o modelo treinado (cache por data de modificação) |
| `ModelService` | Relatório de avaliação (`metrics.json`) |
| `DataQualityService` | Artefatos, qualidade do dataset e pendências |
| `GeoService` | Entrega o GeoJSON configurado |

Repositories: `CoverageRepository` (agregações em DuckDB com parâmetros), `PredictionRepository` (linhas sem rótulo), `ArtifactRepository` (JSON e arquivos).

## Configuração

Variáveis lidas de `.env` / ambiente (ver `.env.example`): `DATA_DIR`, `FEATURES_PATH`, `ML_DATASET_PATH`, `MODEL_PATH`, `METRICS_PATH`, `GEOJSON_PATH`, `GEOJSON_CODE_PROPERTY`, `CORS_ORIGINS`, `APP_ENV`, `LOG_LEVEL`, `API_HOST`, `API_PORT`.

## Testes

```powershell
python -m pytest backend/tests
```

Cobrem health, rotas com e sem dados, repositories, serviços, 404/422, CORS, contrato OpenAPI e sincronia de `docs/api`. Os dados dos testes são sintéticos, em diretório temporário.

## Docker

`backend/Dockerfile` (contexto = raiz do repositório, pois inclui `ml/`). Ver `docker-compose.yml`.
