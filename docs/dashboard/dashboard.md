# Dashboard

Interface principal do projeto (Angular). Todas as páginas consomem a API; sem dados, exibem o motivo informado pelo backend.

| Página | Rota | Conteúdo |
|---|---|---|
| Visão geral | `/dashboard` | Filtros (ano, imunizante, classe), KPIs, mapa, distribuição do déficit, evolução temporal, ranking e indicadores de previsão |
| Histórico | `/cobertura` | Série anual de cobertura/déficit e comparação de até 5 municípios |
| Municípios | `/municipios`, `/municipios/:code` | Tabela paginada e detalhe (histórico e resumo por imunizante) |
| Previsões | `/previsoes` | Classe prevista para o ano seguinte, modelo usado, probabilidades e filtros |
| Modelos | `/modelos` | F1/precision/recall por modelo, baseline, matriz de confusão e importância das features |
| Qualidade dos dados | `/qualidade-dados` | Artefatos presentes/ausentes, nulos, duplicatas e pendências |

## KPIs (visão geral)

| KPI | Cálculo |
|---|---|
| Cobertura média | Média simples de `coverage` das linhas filtradas |
| Déficit médio | Média simples de `deficit` das linhas filtradas |
| Municípios analisados | Municípios distintos nas linhas filtradas |
| Abaixo da meta | Municípios com `deficit > 0` |
| Situação crítica | Municípios com classe `alto` |

O período exibido é o filtro de ano ("todos os anos" quando vazio).

## Mapa

Coroplético por município com três indicadores: classificação de risco, cobertura média e déficit médio. Depende de:

1. `GEOJSON_PATH` apontando para um GeoJSON municipal de São Paulo;
2. `GEOJSON_CODE_PROPERTY` com a propriedade que guarda o código do município, igual ao `municipality_code` dos dados.

Sem esses itens, o mapa mostra "dados geográficos indisponíveis". O repositório não inclui geometrias.

## Filtros

Suportados: ano, imunizante (se a coluna existir nos dados) e classe de déficit. **Região** não é suportada porque não há campo de região no esquema atual.

## Limitação

A lista para o mapa usa até 1000 municípios por requisição (limite da API).
