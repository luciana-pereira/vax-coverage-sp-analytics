import json
import os
import time
from pathlib import Path
from uuid import uuid4

from .http import get_with_retry


def _response_rows(payload):
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        keys = ("data", "items", "results", "records", "doses_aplicadas_pni")
        envelope = next((key for key in keys if key in payload), None)
        if envelope is None:
            raise ValueError("A resposta da fonte não contém uma lista de registros reconhecida.")
        rows = payload[envelope]
    else:
        raise ValueError(
            "A resposta da fonte deve ser uma lista ou um objeto com lista de registros."
        )

    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("A lista retornada pela fonte contém registros inválidos.")
    return rows


def extract_paginated(base_url, endpoint, output: Path, limit=1000, timeout=120, max_pages=None):
    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid4().hex}.tmp")
    offset = 0
    total = 0

    try:
        with temporary.open("w", encoding="utf-8") as file:
            while True:
                response = get_with_retry(
                    url,
                    params={"limit": limit, "offset": offset},
                    timeout=timeout,
                )
                rows = _response_rows(response.json())
                if not rows:
                    break

                for row in rows:
                    file.write(json.dumps(row, ensure_ascii=False) + "\n")

                total += len(rows)
                offset += limit
                print(f"extraídos={total} offset={offset}")

                if max_pages and offset // limit >= max_pages:
                    break
                time.sleep(0.2)
                if len(rows) < limit:
                    break

        if total == 0:
            raise ValueError("A fonte não retornou registros; o arquivo existente foi preservado.")
        os.replace(temporary, output)
        return total
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
