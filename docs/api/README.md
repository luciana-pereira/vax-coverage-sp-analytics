# Documentação da API

Derivada do contrato **real** gerado pelo FastAPI.

| Arquivo | Conteúdo |
|---|---|
| [openapi.json](openapi.json) | Contrato OpenAPI exportado da aplicação |
| [endpoints.md](endpoints.md) | Endpoints, parâmetros, respostas e schemas (gerado) |

Interativo: `/docs` (Swagger UI), `/redoc` e `/openapi.json` no backend em execução.

## Atualização

```powershell
python scripts/export_openapi.py
```

O teste `backend/tests/test_docs_in_sync.py` falha se `openapi.json` divergir da API.

## Convenções

- Todos os endpoints são `GET` e ficam sob `/api/v1`.
- Sem os dados necessários, a resposta é `200` com `status` ≠ `ok`, `message` explicando o motivo e listas vazias:
  `data_unavailable` (dados ausentes), `model_unavailable` (modelo não treinado, em `/predictions`) e `not_trained` (em `/models`).
- `GET /municipalities/{municipality_id}` responde `404` com `{"detail": "..."}` quando o município não tem registros.
- Parâmetros inválidos respondem `422` (validação do FastAPI).
- Filtros comuns: `year`, `year_from`, `year_to`, `immunizer`, `municipality_code` (repetível) e `deficit_class`. Eles filtram **linhas** do dataset de features.
