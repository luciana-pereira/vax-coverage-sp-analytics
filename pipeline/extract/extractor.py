import json
import time
from pathlib import Path

import requests


def extract_paginated(base_url, endpoint, output: Path, limit=1000, timeout=120, max_pages=None):
    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")
    output.parent.mkdir(parents=True, exist_ok=True)

    offset = 0
    total = 0
    mode = "w"

    while True:
        params = {"limit": limit, "offset": offset}
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = (
                payload.get("data")
                or payload.get("items")
                or payload.get("results")
                or payload.get("records")
                or payload.get("doses_aplicadas_pni")
                or []
            )
        else:
            rows = []

        if not rows:
            break

        with output.open(mode, encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        mode = "a"
        total += len(rows)
        offset += limit

        print(f"extraídos={total} offset={offset}")

        if max_pages and offset // limit >= max_pages:
            break

        # Evita martelar a API; ajuste conforme a política do serviço.
        time.sleep(0.2)

        if len(rows) < limit:
            break

    return total
