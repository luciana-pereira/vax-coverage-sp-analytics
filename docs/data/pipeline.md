# Pipeline de dados

Código em `pipeline/`. Cada etapa é reproduzível e lê/grava em `data/` (ou `DATA_DIR`).

```text
extract   -> data/raw/<RAW_FILE_NAME>              (JSONL, um registro por linha)
transform -> data/processed/vaccination.parquet    (esquema canônico)
validate  -> relatório no log; código de saída 1 se houver problemas
load      -> data/processed/vax.duckdb (tabela "vaccination")
```

Execute com o `.venv` ativo, na raiz: `python -m pipeline.cli <extract|transform|validate|load>`.

## extract

Requisições paginadas (`limit`/`offset`) ao endpoint PNI configurado. A resposta observada usa o envelope `doses_aplicadas_pni`; uma amostra de uma página foi validada, mas a extração completa ainda não foi executada. Os registros brutos são gravados em JSONL por página.

O extrator aceita respostas em lista, nos envelopes genéricos (`data`, `items`, `results`, `records`) e no envelope PNI observado (`doses_aplicadas_pni`).

## transform

1. Lê o JSONL, deriva `year` de `dt_vacina` ou `data_vacina`, conta cada registro PNI como uma dose (quando há `codigo_documento` ou `sg_imunobiologico`) e filtra `sigla_uf_paciente` quando disponível.
2. Normaliza nomes de colunas. `DEDUPLICATE_RAW=false` é obrigatório para o raw reduzido sem identificador único; linhas iguais podem ser doses distintas.
3. Aplica `data/external/column_mapping.json` ao schema do raw local: `co_municipio_paciente`, `no_municipio_paciente`, `sg_imunobiologico`.
4. Sempre exige `data/external/target_population.csv` e anexa pelo município, ano e imunizante. População embutida no bruto e população total SIDRA são ignoradas como denominador. Ausência, duplicidade, divergência ou falta de correspondência bloqueia a escrita do Parquet.

### Mapeamento de colunas

`data/external/column_mapping.json` (chaves canônicas; valores = nomes na fonte **depois da normalização**):

```json
{
  "municipality_code": "co_municipio_paciente",
  "municipality_name": "no_municipio_paciente",
  "immunizer": "sg_imunobiologico"
}
```

`year` e `doses` são derivados pelo loader para o raw reduzido. O endpoint PNI completo tem schema diferente; seu `codigo_vacina` não é mapeado para `immunizer` sem cruzamento oficial.

### População-alvo

`data/external/target_population.csv` com `municipality_code, year, immunizer, population`. O target deve ser único por chave e corresponder a cada grupo do Parquet. O validador compara os valores de `population` com o CSV; município sem correspondência, denominação duplicada ou divergente invalida o dataset.

## validate

Verifica: `municipality_code`, `immunizer`, `year`, `doses`, `population`, nulos, tipos numéricos, duplicatas, valores negativos, população zero, anos inválidos e alinhamento exato com `target_population.csv`.

## load

Cria/substitui a tabela `vaccination` no DuckDB para análise local. A API lê o Parquet de features diretamente.

## Lacunas conhecidas

| Lacuna | Impacto |
|---|---|
| Extração PNI integral e duplicidade | A amostra de uma página não valida todos os registros nem a política de deduplicação |
| API PNI completa | `codigo_vacina` requer cruzamento oficial; o raw reduzido local usa `sg_imunobiologico` |
| População-alvo por imunizante | `target_population.csv` não está presente; sem ele não há cobertura derivada do PNI |
| Mapeamento de idade para vacina | O helper requer mapping explícito; não há associação aprovada para `SCR`/`INF3` |
| Metas por imunizante | `coverage_targets.json` não está presente; ML bloqueia o default não referenciado |
| GeoJSON municipal | Não está presente; o mapa permanece indisponível |
