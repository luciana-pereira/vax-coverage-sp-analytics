# Streamlit (legado)

Dashboard original, mantido temporariamente. **Não é a arquitetura final**; será removido quando o Angular tiver paridade funcional.

Lê `data/processed/features.parquet` e `data/models/metrics.json` diretamente.

```bash
pip install -r legacy/streamlit/requirements.txt
streamlit run legacy/streamlit/app.py
```
