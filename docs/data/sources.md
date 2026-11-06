# Fontes de dados

## Ministério da Saúde: PNI

Endpoint: `https://apidadosabertos.saude.gov.br/vacinacao/doses-aplicadas-pni-2024`.

Validado em 05/11/2026 com requisições limitadas (`limit`/`offset`): HTTP 200; o corpo é um objeto com a lista `doses_aplicadas_pni`. A resposta completa observada inclui `data_vacina`, `codigo_municipio_paciente`, `nome_municipio_paciente`, `codigo_vacina` e `sigla_uf_paciente`. `codigo_vacina` é um código do produto e não foi cruzado oficialmente para um rótulo de imunizante.

O raw local disponível, `data/raw/pni_2024_sp_min.jsonl`, tem 2.401.483 linhas válidas, todas de 2024, 645 códigos municipais e 90 valores distintos de imunizante. Seu schema reduzido é `co_municipio_paciente`, `no_municipio_paciente`, `dt_vacina`, `sg_imunobiologico`; este último é o campo que identifica o imunizante neste arquivo. Não há ID de dose no raw reduzido, então linhas idênticas não podem ser descartadas com segurança e a deduplicação está desativada.

O schema da API completa e o raw reduzido são diferentes. A configuração local mapeia o raw para `sg_imunobiologico`. Não mapear `codigo_vacina` da API diretamente como imunizante sem um dicionário oficial.

## IBGE: SIDRA

Consulta validada em 05/11/2026:

`https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2024`

A resposta foi HTTP 200 e continha 645 municípios paulistas após o filtro de código estadual `35`. No contrato SIDRA observado, `D1C`/`D1N` são código/nome do município, `D2C` é o código da variável, `D3C` é o período e `V` é o valor.

Essa variável fornece população municipal total estimada para 2024. Ela não é denominador vacinal por idade/imunizante e não deve ser usada diretamente no cálculo de cobertura. O pipeline exige `data/external/target_population.csv` quando a entrada ainda não traz `population` canônica.

Também foram consultados a tabela censitária SIDRA 9514, variável 93, para 2022 (população total de 645 municípios) e os códigos de idade retornados: 0–4 e 60–64 até 100+. O helper de estimativa exige um mapeamento idade→imunizante explícito; não existe mapeamento aprovado no workspace, portanto nenhum denominador vacinal foi produzido.

## Regra de ouro

Não usar nome do município como chave primária de integração. Preferir código oficial do município.

## Lacunas pendentes

- Extração integral e validação de paginação/falhas da API PNI.
- Cruzamento oficial de `codigo_vacina` da API completa para rótulos de imunizante.
- Validação metodológica da associação entre imunizantes PNI e faixas etárias do IBGE.
- Arquivo de população-alvo por município, ano e imunizante (não presente no workspace).
- Arquivo de metas por imunizante (não presente; não se aplica o default de 95% no CLI de ML).
- GeoJSON municipal de São Paulo e a propriedade com o código do município.

O pipeline falha explicitamente quando o denominador-alvo não está configurado; ele não substitui esse dado por população municipal total. Consulte [pipeline.md](pipeline.md).
