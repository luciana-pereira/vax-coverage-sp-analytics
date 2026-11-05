# Frontend (Angular)

Dashboard do Vax Coverage SP Analytics. Angular 19, TypeScript estrito, componentes standalone, signals e rotas com lazy loading.

## Execução

```bash
npm ci            # ou ./scripts/bootstrap
npm start         # http://localhost:4200 (usa environment.development.ts)
```

Requer o backend em `http://localhost:8000`.

## Build e testes

```bash
npm run build     # dist/frontend/browser
npm test          # Jasmine/Karma em Chrome headless (precisa do Chrome instalado)
npm run test:watch
```

## Configuração de ambiente

`src/environments/environment.ts` (produção) e `environment.development.ts` (`ng serve`) definem `apiBaseUrl` (padrão `http://localhost:8000/api/v1`). O valor é injetado por `API_BASE_URL`; nenhum componente usa URL literal.

## Arquitetura

```text
src/app/
  core/       API_BASE_URL, tipos da API, services HTTP, errorInterceptor, FilterStore
  shared/     kpi-card, chart, choropleth-map, filters-bar, state-panel, risk-badge, utils
  layout/     shell, header, sidebar
  features/   dashboard, coverage, municipalities, predictions, models, data-quality
```

- HTTP apenas em `core/services` (`CoverageService`, `MunicipalitiesService`, `PredictionsService`, `ModelsService`, `DataQualityService`, `GeoService`).
- Filtros globais (ano, imunizante, classe) em `FilterStore` (signals).
- Cada tela trata carregando, erro, vazio e "dados indisponíveis".

## Features

| Feature | Rota |
|---|---|
| `dashboard` | `/dashboard` |
| `coverage` | `/cobertura` |
| `municipalities` | `/municipios`, `/municipios/:code` |
| `predictions` | `/previsoes` |
| `models` | `/modelos` |
| `data-quality` | `/qualidade-dados` |

Detalhes: [docs/frontend/frontend.md](../docs/frontend/frontend.md) e [docs/dashboard/dashboard.md](../docs/dashboard/dashboard.md).

## Dependências além do Angular

| Pacote | Uso |
|---|---|
| `chart.js` | Gráficos de linha, barras e rosca |
| `d3-geo` (+ `@types/d3-geo`) | Projeção e desenho do mapa a partir de GeoJSON |
