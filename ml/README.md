# ml/

Machine Learning do projeto. Treino e inferência são separados.

| Pasta | Responsabilidade |
|---|---|
| `features/` | Cobertura, déficit, classe e dataset supervisionado (alvo no ano seguinte) |
| `training/` | Treino com validação temporal e escolha do modelo |
| `evaluation/` | Métricas de classificação e leitura do relatório |
| `inference/` | Carregar modelo e prever (usado pela API) |
| `models/` | Candidatos (Logistic Regression, Random Forest, Gradient Boosting) e pré-processamento |

CLI: `python -m ml.cli <features|train|evaluate|predict>`. Documentação: [docs/ml/ml-pipeline.md](../docs/ml/ml-pipeline.md).
