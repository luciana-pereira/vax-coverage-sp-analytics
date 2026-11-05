# Machine Learning

Código em `ml/` (`features`, `training`, `evaluation`, `inference`, `models`). Execução pelo CLI: `python -m ml.cli <features|train|evaluate|predict>`.

## Problema

Classificação multiclasse: prever a **classe de déficit do ano seguinte** (`baixo`, `moderado`, `alto`) de cada município (e imunizante, quando existir).

| Item | Definição |
|---|---|
| Target | `deficit_class_next` (classe de déficit em `t+1` da mesma entidade) |
| Features | `coverage`, `deficit`, `doses`, `population`, `year`, `coverage_prev`, `deficit_prev`, `coverage_delta` e `immunizer` (categórica, se existir) |
| Excluídas | `deficit_class` (derivada de `coverage`/`deficit`) e o próprio alvo |
| Split | Temporal: treino < validação < teste |
| Métrica de seleção | F1 macro |

Por que `t+1`: a classe do ano `t` é função de `coverage` e `deficit` do mesmo ano. Usá-las para predizer a própria classe seria vazamento de alvo. Com o alvo no ano seguinte, os atributos do ano corrente são informação legítima.

## Modelos comparados

Logistic Regression, Random Forest (`class_weight=balanced`) e Gradient Boosting, em um `Pipeline` com imputação, padronização e one-hot (`ml/models/`).

## Validação temporal

- 3+ períodos rotulados: treino = anos mais antigos, validação = penúltimo, teste = último. O modelo é escolhido pelo F1 macro na **validação**, retreinado com treino + validação e avaliado no **teste**.
- 2 períodos: não há validação separada; a escolha usa o teste e isso é registrado em `selection.note` (resultado otimista).
- Menos de 2 períodos: o treino é recusado.

## Métricas e relatório

`data/models/metrics.json` (também servido em `GET /api/v1/models`) traz: alvo, features, classes, anos do split e tamanhos, métricas por modelo (accuracy, precision/recall/F1 macro e ponderados, matriz de confusão), baseline, importância das features do modelo escolhido e data de geração.

O **baseline de persistência** prevê a classe do ano `t+1` igual à do ano `t`: um modelo só tem valor se superá-lo.

RMSE/MAE não se aplicam: não há regressão implementada.

## Inferência

`ml.inference` carrega o modelo e retorna classe e probabilidades por classe. A API aplica o modelo às linhas do último ano sem rótulo em `ml_dataset.parquet` (previsão para o ano seguinte).

## Reprodutibilidade

`ML_RANDOM_STATE` (padrão 42). O treino só depende dos arquivos em `data/processed`.

## Resultados

Nenhum resultado é registrado neste repositório: dependem dos dados reais, que ainda não foram carregados.
