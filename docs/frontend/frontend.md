# Frontend

Angular 19 (componentes standalone, signals, rotas com lazy loading), em `frontend/`. Visão geral e comandos em [frontend/README.md](../../frontend/README.md).

## Arquitetura

```text
src/app/
  core/       config (API_BASE_URL), models (tipos da API), services (HTTP), interceptors, state (filtros)
  shared/     components (kpi-card, chart, choropleth-map, filters-bar, state-panel, risk-badge), state, utils
  layout/     shell, header, sidebar
  features/   dashboard, coverage, municipalities, predictions, models, data-quality
```

- **HTTP só em services** (`core/services`). Nenhum componente conhece a URL da API.
- **URL por ambiente**: `src/environments/environment.ts` (produção) e `environment.development.ts` (substituído no `ng serve`), injetada via `API_BASE_URL`.
- **Erros**: `errorInterceptor` converte falhas em `ApiError` com mensagem legível (inclusive "API indisponível").
- **Estados**: `loadOnChange`/`loadOnce` expõem `loading | error | success`; cada tela trata carregando, erro, vazio e "dados indisponíveis".
- **Tipos**: `core/models/api.models.ts` espelha os schemas do OpenAPI (`docs/api/openapi.json`).

## Gráficos e mapa

Gráficos com Chart.js (`ChartComponent`). O mapa usa d3-geo para projetar um GeoJSON **fornecido pela API**; sem GeoJSON mostra "dados indisponíveis" e não simula municípios.

## Acessibilidade e responsividade

Link "Ir para o conteúdo", `label` em todos os filtros, foco visível, `role`/`aria-label` em gráficos e mapa, navegação por teclado nas formas do mapa e layout que colapsa a barra lateral em telas estreitas.
