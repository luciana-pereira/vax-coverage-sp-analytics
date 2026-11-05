# Fontes de dados

## Ministério da Saúde: PNI

Endpoint: `https://apidadosabertos.saude.gov.br/vacinacao/doses-aplicadas-pni-2024`.

Validado em 05/11/2026 com requisições limitadas (`limit`/`offset`): HTTP 200; o corpo é um objeto com a lista `doses_aplicadas_pni`. Foram observados os campos `data_vacina`, `codigo_municipio_paciente`, `nome_municipio_paciente`, `codigo_vacina` e `sigla_uf_paciente`. Uma página de 1.000 registros foi lida pelo extrator e 201 registros da amostra eram de SP; a extração completa não foi executada.

O pipeline deriva o ano de `data_vacina`, filtra pela UF do paciente e mantém `codigo_vacina` como código bruto. O dicionário oficial e o cruzamento desses códigos para grupos vacinais ainda não foram validados; portanto, não se deve interpretar esses códigos automaticamente como SCR, INF3 ou outro grupo.

## IBGE: SIDRA

Consulta validada em 05/11/2026:

`https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2024`

A resposta foi HTTP 200 e continha 645 municípios paulistas após o filtro de código estadual `35`. No contrato SIDRA observado, `D1C`/`D1N` são código/nome do município, `D2C` é o código da variável, `D3C` é o período e `V` é o valor.

Essa variável fornece população municipal total estimada para 2024. Ela não é denominador vacinal por idade/imunizante e não deve ser usada diretamente no cálculo de cobertura. O pipeline exige `data/external/target_population.csv` quando a entrada ainda não traz `population` canônica.

## Regra de ouro

Não usar nome do município como chave primária de integração. Preferir código oficial do município.

## Lacunas pendentes

- Extração integral e validação de paginação/falhas da API PNI.
- Cruzamento oficial de `codigo_vacina` para imunizantes/grupos e denominadores por faixa etária.
- Arquivo de população-alvo por município, ano e imunizante (não presente no workspace).
- GeoJSON municipal de São Paulo e a propriedade com o código do município.

O pipeline falha explicitamente quando o denominador-alvo não está configurado; ele não substitui esse dado por população municipal total. Consulte [pipeline.md](pipeline.md).
