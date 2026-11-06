import json

import pytest
import requests

from pipeline.extract.extractor import extract_paginated
from pipeline.extract.http import get_with_retry


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


def test_extract_paginated_reads_pni_response_envelope(tmp_path, monkeypatch):
    responses = {
        0: {"doses_aplicadas_pni": [{"id": "first"}, {"id": "second"}]},
        2: {"doses_aplicadas_pni": []},
    }

    def fake_get(url, params, timeout):
        return FakeResponse(responses[params["offset"]])

    monkeypatch.setattr("pipeline.extract.http.requests.get", fake_get)
    monkeypatch.setattr("pipeline.extract.extractor.time.sleep", lambda _: None)
    output = tmp_path / "pni.jsonl"

    total = extract_paginated(
        "https://pni.example",
        "/vacinacao/doses-aplicadas-pni-2024",
        output,
        limit=2,
        timeout=10,
    )

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert total == 2
    assert rows == [{"id": "first"}, {"id": "second"}]


def test_extract_paginated_retries_transient_server_errors(tmp_path, monkeypatch):
    attempts = 0

    def fake_get(url, params, timeout):
        nonlocal attempts
        if params["offset"] == 0:
            attempts += 1
            if attempts == 1:
                return FakeResponse({}, status_code=503)
            return FakeResponse({"doses_aplicadas_pni": [{"id": "accepted"}]})
        return FakeResponse({"doses_aplicadas_pni": []})

    monkeypatch.setattr("pipeline.extract.http.requests.get", fake_get)
    monkeypatch.setattr("pipeline.extract.extractor.time.sleep", lambda _: None)

    output = tmp_path / "pni.jsonl"
    total = extract_paginated("https://pni.example", "/data", output, limit=1, max_pages=2)

    assert attempts == 2
    assert total == 1
    assert json.loads(output.read_text(encoding="utf-8")) == {"id": "accepted"}


def test_extract_failure_preserves_previous_raw_file(tmp_path, monkeypatch):
    output = tmp_path / "pni.jsonl"
    output.write_text('{"id":"previous"}\n', encoding="utf-8")

    def fake_get(url, params, timeout):
        if params["offset"] == 0:
            return FakeResponse({"doses_aplicadas_pni": [{"id": "new-1"}, {"id": "new-2"}]})
        raise requests.Timeout("source timed out")

    monkeypatch.setattr("pipeline.extract.http.requests.get", fake_get)
    monkeypatch.setattr("pipeline.extract.extractor.time.sleep", lambda _: None)

    with pytest.raises(requests.Timeout):
        extract_paginated("https://pni.example", "/data", output, limit=2)

    assert output.read_text(encoding="utf-8") == '{"id":"previous"}\n'
    assert list(tmp_path.glob("*.tmp")) == []


def test_http_get_retries_429_and_returns_a_valid_response(monkeypatch):
    attempts = 0

    def fake_get(url, params, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return FakeResponse({}, status_code=429)
        return FakeResponse({"ok": True})

    monkeypatch.setattr("pipeline.extract.http.requests.get", fake_get)
    monkeypatch.setattr("pipeline.extract.http.time.sleep", lambda _: None)

    response = get_with_retry("https://source.example", params={"year": 2024}, timeout=2)

    assert response.json() == {"ok": True}
    assert attempts == 2


def test_http_get_retries_timeout_but_surfaces_nonretryable_status(monkeypatch):
    attempts = 0

    def fake_get(url, params, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise requests.Timeout("temporary")
        return FakeResponse({}, status_code=400)

    monkeypatch.setattr("pipeline.extract.http.requests.get", fake_get)
    monkeypatch.setattr("pipeline.extract.http.time.sleep", lambda _: None)

    with pytest.raises(requests.HTTPError):
        get_with_retry("https://source.example", timeout=2)

    assert attempts == 2
