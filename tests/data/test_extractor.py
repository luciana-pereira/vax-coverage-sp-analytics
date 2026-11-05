import json

from pipeline.extract.extractor import extract_paginated


def test_extract_paginated_reads_pni_response_envelope(tmp_path, monkeypatch):
    responses = {
        0: {"doses_aplicadas_pni": [{"id": "first"}, {"id": "second"}]},
        2: {"doses_aplicadas_pni": []},
    }

    def fake_get(url, params, timeout):
        return FakeResponse(responses[params["offset"]])

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    monkeypatch.setattr("pipeline.extract.extractor.requests.get", fake_get)
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
