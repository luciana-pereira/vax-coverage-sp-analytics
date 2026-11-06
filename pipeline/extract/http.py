from __future__ import annotations

import time

import requests

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_with_retry(
    url: str,
    *,
    params: dict | None = None,
    timeout: int = 120,
    retries: int = 3,
    backoff_seconds: float = 0.5,
) -> requests.Response:
    """GET with bounded retries for transient network and server failures."""
    if retries < 1:
        raise ValueError("retries must be at least one")

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError):
            if attempt + 1 == retries:
                raise
            time.sleep(min(backoff_seconds * (2**attempt), 2.0))
            continue

        status_code = getattr(response, "status_code", 200)
        if status_code in RETRYABLE_STATUS_CODES and attempt + 1 < retries:
            time.sleep(min(backoff_seconds * (2**attempt), 2.0))
            continue

        response.raise_for_status()
        return response

    raise RuntimeError("Número inesperado de tentativas HTTP esgotado.")
