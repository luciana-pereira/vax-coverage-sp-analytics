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

1. Lê o JSONL, deriva `year` de `data_vacina`, conta um registro como uma dose quando `codigo_documento` está presente e filtra `sigla_uf_paciente` pela UF configurada.
2. Normaliza nomes de colunas e remove linhas idênticas (`DEDUPLICATE_RAW=true`). A regra de duplicidade ainda requer validação na extração integral.
3. Aplica `data/external/column_mapping.json`, atualmente com `codigo_municipio_paciente`, `nome_municipio_paciente` e `codigo_vacina`.
4. Se não houver `population` canônica, lê `data/external/target_population.csv`; sem esse arquivo, falha. A população total da SIDRA não é usada como denominador.

### Mapeamento de colunas

`data/external/column_mapping.json` (chaves canônicas; valores = nomes na fonte **depois da normalização**):

```json
{
  "municipality_code": "codigo_municipio_paciente",
  "municipality_name": "nome_municipio_paciente",
  "immunizer": "codigo_vacina"
}
```

`year` e `doses` são derivados pelo loader para o schema PNI observado. `municipality_name` e `immunizer` são opcionais no contrato geral; no PNI, `codigo_vacina` permanece código bruto até existir cruzamento validado.

### População-alvo

`data/external/target_population.csv` com `municipality_code, year, [immunizer], population`. Inclua `immunizer` para denominadores por vacina/faixa etária; o join usa essa dimensão quando presente. A ausência do arquivo é erro explícito, e municípios sem correspondência ficam sem população/cobertura válida.

## validate

Verifica: colunas obrigatórias (`municipality_code`, `year`, `doses`, `population`), dataset vazio, duplicatas, valores negativos, população zero e anos não numéricos.

## load

Cria/substitui a tabela `vaccination` no DuckDB para análise local. A API lê o Parquet de features diretamente.

## Lacunas conhecidas

| Lacuna | Impacto |
|---|---|
| Extração PNI integral e duplicidade | A amostra de uma página não valida todos os registros nem a política de deduplicação |
| Cruzamento dos códigos PNI | `codigo_vacina` não foi mapeado oficialmente para SCR/INF3 ou grupos etários |
| População-alvo por imunizante | `target_population.csv` não está presente; sem ele não há cobertura derivada do PNI |
| Metas por imunizante | Usa a meta padrão enquanto o arquivo não existir |
| Filtro por UF/município (`TARGET_UF`) | Variável reservada; o filtro ainda não existe |
