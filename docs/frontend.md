# Frontend Angular — Vax Coverage SP Analytics

Este documento descreve a aplicação web em `frontend/`, suas rotas, integração com a API, visualizações e processo de build. Para os contratos REST e o pipeline de dados, consulte [backend e ML](backend.md) e [endpoints](api/endpoints.md).

## 1. Arquitetura SPA

O frontend é uma **single-page application (SPA)** em Angular 19 e TypeScript, com componentes standalone, signals e carregamento das páginas sob demanda por `loadComponent`. O Angular Router troca o conteúdo do `router-outlet` sem substituir o shell compartilhado. O projeto usa SCSS para estilos globais, Chart.js para gráficos e d3-geo para projeção geográfica.

```text
frontend/src/
  main.ts                     Inicialização da aplicação
  app/
    app.component.ts          Raiz da aplicação
    app.config.ts             Router, HTTP, interceptors e locale pt-BR
    app.routes.ts             Rotas e carregamento lazy das páginas
    layout/                   Shell, cabeçalho e sidebar
    core/
      config/                 Configuração da URL da API
      models/                 Tipos dos contratos HTTP
      services/               Cliente HTTP e serviços de domínio
      interceptors/           Tratamento de erros da API
      state/                  Filtros e tema
    shared/
      components/             Gráfico, mapa, filtros, KPIs e estados
      state/                  Gerenciamento de carregamento
      utils/                  Formatação e configuração de gráficos
    features/                 Páginas por funcionalidade
  environments/               Configuração da API por ambiente
  styles.scss                 Tokens, componentes visuais e responsividade
```

O `ShellComponent` mantém a navegação e envolve o cabeçalho e o `router-outlet` em `<main>`. Os serviços em `core/services` comunicam-se com a API via `ApiClient`; componentes não acessam diretamente DuckDB ou Parquet. Os estados de carregamento, erro, ausência de dados e resultados vazios são apresentados explicitamente.

O `errorInterceptor` converte falhas HTTP em mensagens de erro legíveis. Os helpers `loadOnChange` e `loadOnce` administram estados assíncronos, e `core/models/api.models.ts` define os tipos usados para as respostas da API.

### Rotas

| Rota | Página | Responsabilidade |
|---|---|---|
| `/dashboard` | Visão geral | Indicadores, análises agregadas, mapa, evolução e ranking. |
| `/cobertura` | Histórico | Evolução da cobertura e comparação de municípios. |
| `/municipios` | Municípios | Lista e análise de municípios. |
| `/municipios/:code` | Detalhe do município | Indicadores e informações de um município. |
| `/previsoes` | Previsões | Predições de déficit produzidas pela API. |
| `/modelos` | Modelos | Relatório e métricas dos modelos treinados. |
| `/qualidade-dados` | Qualidade dos dados | Estado dos artefatos e lacunas de dados. |

A rota vazia e caminhos desconhecidos redirecionam para `/dashboard`. As páginas são definidas em `app.routes.ts`; não há módulos Angular de rotas separados.

### Configuração e comunicação

`src/environments/environment.ts` define `apiBaseUrl` para produção; `environment.development.ts` é usado pelo servidor de desenvolvimento. Atualmente ambos apontam para `http://localhost:8000/api/v1`. O valor é injetado por `API_BASE_URL` em `app.config.ts`.

Para implantação, configure a URL acessível **pelo navegador do usuário** antes do build. `localhost` em um navegador remoto aponta para a máquina do usuário, não para o servidor da aplicação. Quando frontend e API têm origens diferentes, configure `CORS_ORIGINS` no backend e verifique os métodos permitidos para cada fluxo.

Os serviços incluem `CoverageService`, `MunicipalitiesService`, `PredictionsService`, `ModelsService`, `DataQualityService`, `GeoService` e `VaccinationAnalyticsService`. O `FilterStore` compartilha filtros de cobertura; o painel de análises agregadas mantém filtros próprios e usa `VaccinationAnalyticsSession` para armazenar o token temporário do CSV.

## 2. Integração geográfica e mapa

O mapa coroplético utiliza o `ChoroplethMapComponent` e **d3-geo**, não Leaflet. O arquivo não é carregado diretamente pelo navegador a partir de `data/`: o backend lê o GeoJSON configurado e o disponibiliza em `GET /api/v1/geo/municipalities`.

### Configuração

O caminho padrão do backend é `data/external/sp_municipios.geojson`, ajustável por `GEOJSON_PATH`. O arquivo deve ser um GeoJSON `FeatureCollection` com uma lista `features`. Configure `GEOJSON_CODE_PROPERTY` com o nome real da propriedade que identifica o município em cada feature:

```dotenv
GEOJSON_PATH=data/external/sp_municipios.geojson
GEOJSON_CODE_PROPERTY=nome_da_propriedade_do_codigo
```

O nome acima é um **placeholder**, não um valor universal: inspecione o GeoJSON fornecido antes de configurar. O arquivo e a propriedade precisam corresponder aos dados efetivamente carregados. Sem o arquivo ou a propriedade configurada, o componente exibe estado de indisponibilidade, sem inventar geometrias.

### Cruzamento dos códigos

1. `GeoService` do frontend obtém o GeoJSON e `code_property` da API; os dados municipais vêm de `GET /api/v1/municipalities`.
2. O componente cria um índice dos indicadores por `municipality_code`.
3. Para cada feature, lê `feature.properties[code_property]`, converte o valor com `String(...)` e procura a **correspondência exata** no índice.
4. As geometrias sem indicador correspondente recebem a cor de “sem dados”; a legenda e o título de cada forma informam o contexto.

**Importante:** o frontend não reduz nem normaliza códigos IBGE. Se o dataset usar códigos de seis dígitos, a propriedade geográfica também deve conter o mesmo código de seis dígitos, com a mesma representação textual. Um GeoJSON com código IBGE de sete dígitos não será associado automaticamente: normalize previamente as fontes conforme o identificador adotado e valide o cruzamento. A configuração correta da propriedade, por si só, não valida seu conteúdo.

`geoMercator().fitSize(...)` ajusta a projeção ao SVG de `800 × 520`, e `geoPath` gera as formas. O usuário alterna entre classificação de risco, cobertura média e déficit médio; cada município pode ser selecionado por clique ou Enter. A disponibilidade do mapa na visão geral também depende de dados de cobertura e da resposta de municípios.

## 3. Componentes de visualização

### Gráficos

`ChartComponent` encapsula Chart.js, atualiza o gráfico quando a configuração muda e destrói a instância ao sair da página. Além do canvas com `aria-label`, apresenta uma tabela expansível com os valores, acessível a leitores de tela. Há gráficos de linha, barras e rosca para indicadores e análises.

`VaccinationAnalyticsPanelComponent` consulta `/analytics` e apresenta, conforme a página e a disponibilidade dos dados:

- doses aplicadas por mês e por vacina;
- **doses por sexo**, conforme o campo informado pela fonte; o frontend não infere gênero ou identidade de gênero a partir dele;
- doses por faixa etária, com gráfico das faixas `0-4` e `60+` quando disponíveis;
- agregações por município na respectiva visão, sujeitas às verificações de abrangência e dimensão da fonte.

Os filtros de analytics contemplam ano, vacina, faixa etária, município e base municipal. Os dados do paciente e do estabelecimento de aplicação são tratados como dimensões diferentes. Sem a dimensão necessária ou sem valores para os filtros, o painel informa indisponibilidade ou resultado vazio em vez de fabricar dados.

Na visão geral, o usuário pode enviar CSV para análise agregada temporária. O controle usa input nativo com rótulo, descrição, indicação de progresso e mensagens de erro. O backend valida e agrega o arquivo; o upload não treina modelos nem substitui o pipeline de cobertura. Consulte [backend e ML](backend.md#analytics-e-upload-csv).

### Layout responsivo e tema

Os estilos estão em `frontend/src/styles.scss`:

- Em larguras **acima de 768 px**, o host de `app-sidebar` fica fixo à esquerda (`position: fixed`), com largura de 260 px e altura da viewport. O corpo usa `overflow: hidden`; `<main>` ocupa o espaço restante e possui `overflow-y: auto`, incluindo o cabeçalho e a página no seu fluxo.
- A própria sidebar também permite scroll quando seu conteúdo não cabe na altura disponível; portanto, o scroll não é literalmente exclusivo do painel principal em todos os casos. Tabelas largas podem ter scroll horizontal próprio.
- Em **768 px ou menos**, a sidebar deixa de ser fixa e passa a ocupar uma faixa superior com menu expansível; `<main>` continua com scroll próprio. O menu pode rolar quando aberto em uma viewport baixa.
- Até **1024 px**, as grades de mapa e duas colunas passam a uma coluna; até **600 px**, padding, filtros e altura dos gráficos são ajustados.
- As seções e grades usam espaçamento de 32 px; os cards compartilham bordas arredondadas e sombra. Os tokens de cor têm variantes clara e escura.

O `ThemeService` aplica o tema em `data-theme` no elemento raiz e tenta preservar a escolha em `localStorage`, com preferência do sistema como valor inicial quando não há escolha salva.

### Acessibilidade

A aplicação oferece link para saltar ao conteúdo principal, foco visível, labels nos filtros, indicação de página ativa na sidebar, tabela alternativa para gráficos e formas do mapa selecionáveis por teclado. As mensagens de carregamento, erros e dados ausentes usam os componentes de estado. Ao alterar visualizações, preserve os rótulos e a alternativa textual, além do comportamento por teclado.

## 4. Desenvolvimento, testes e build

### Pré-requisitos

Instale uma versão de Node.js e npm compatível com Angular 19; o bootstrap do repositório exige Node 20.11 ou superior. Consulte também a [matriz oficial do Angular](https://angular.dev/reference/versions). O Chrome é necessário para a configuração padrão dos testes Karma.

### Desenvolvimento local

Em PowerShell, na raiz do repositório:

```powershell
Set-Location frontend
npm ci
npm start
```

Abra `http://localhost:4200` e inicie a API separadamente em `http://localhost:8000`; as instruções do servidor estão em [backend e ML](backend.md#5-configuração-e-operação). Use `Ctrl+C` para encerrar o servidor de desenvolvimento.

### Build de produção

No diretório `frontend/`:

```powershell
npm run build
```

O comando executa `ng build` com a configuração `production` por padrão, conforme `angular.json`. O output da aplicação para navegador fica em `frontend/dist/frontend/browser/`; os nomes dos arquivos são gerados com hash. Os budgets configurados em `angular.json` podem gerar avisos ou interromper o build quando os limites são ultrapassados.

O servidor de hospedagem precisa servir o conteúdo do diretório de saída e tratar rotas da SPA com fallback para `index.html` em navegações diretas. Verifique a URL da API, o CORS e a disponibilidade dos artefatos antes de publicar; gerar o build não inicia o backend nem prepara os dados.

### Testes

```powershell
npm test
npm run test:watch
```

`npm test` executa Jasmine/Karma sem watch, usando Chrome headless pela configuração do projeto. Consulte também o [guia do dashboard](dashboard/dashboard.md) e o [README principal](../README.md).
