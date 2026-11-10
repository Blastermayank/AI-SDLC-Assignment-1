"""The API key never leaves the server; logs hold no bodies, code or model output.

SC-005, FR-050, FR-055; task T052.
"""

import json
import logging
from pathlib import Path

import httpx
import pytest
from google.genai import errors

STATIC = Path(__file__).resolve().parents[1] / "static"
CODE_MARKER = "SWEEP-CODE-MARKER-91c2"
OUTPUT_MARKER = "SWEEP-OUTPUT-MARKER-4e7a"

GET_PATHS = [
    "/",
    "/api/health",
    "/api/part-1a/tiers",
    "/api/part-1a/harness",
    "/api/part-1b/evaluation",
    "/api/part-1b/evaluation/history",
    "/api/evidence",
    "/api/evidence/1b-src",
    "/api/evidence/no-such-item",
    "/api/openapi.json",
    "/does-not-exist",
]

OUTPUT = json.dumps({
    "status": "success",
    "findings": [{"vulnerability": "Code Injection", "severity": "High",
                  "description": OUTPUT_MARKER, "evidence": "eval", "remediation": "Avoid eval."}],
})
BEHAVIOURS = [
    OUTPUT,
    errors.ClientError(429, {"error": {"code": 429, "message": "quota"}}),
    errors.ClientError(403, {"error": {"code": 403, "message": "denied"}}),
    errors.ServerError(503, {"error": {"code": 503, "message": "overloaded"}}),
    httpx.ConnectError("unreachable"),
    "not json",
]


def responses_text(response):
    return response.text + json.dumps(dict(response.headers))


def test_key_never_in_responses_headers_or_static_assets(client, sentinel_key, fake_gemini):
    seen = []
    for path in GET_PATHS:
        seen.append(responses_text(client.get(path)))
    for asset in STATIC.rglob("*"):
        if asset.is_file():
            url = "/static/" + asset.relative_to(STATIC).as_posix()
            seen.append(responses_text(client.get(url)))
    seen.append(responses_text(client.post("/api/part-1a/request",
                                           json={"client_id": "sweep", "tier": "free"})))
    seen.append(responses_text(client.post("/api/part-1a/reset")))
    for behaviour in BEHAVIOURS:
        fake_gemini(behaviour)
        seen.append(responses_text(client.post("/api/part-1b/analyze",
                                               json={"code": f"eval(x)  # {CODE_MARKER}"})))
    for text in seen:
        assert sentinel_key not in text


@pytest.mark.parametrize("behaviour", BEHAVIOURS, ids=range(len(BEHAVIOURS)))
def test_logs_hold_no_key_code_output_or_bodies(client, sentinel_key, fake_gemini, caplog,
                                                behaviour):
    fake_gemini(behaviour)
    with caplog.at_level(logging.DEBUG):
        client.post("/api/part-1b/analyze", json={"code": f"eval(x)  # {CODE_MARKER}"})
        client.post("/api/part-1a/request", json={"client_id": "log-sweep", "tier": "free"})
    assert caplog.records, "expected request log lines"
    for record in caplog.records:
        message = record.getMessage()
        for forbidden in (sentinel_key, CODE_MARKER, OUTPUT_MARKER, "log-sweep", '"code"'):
            assert forbidden not in message, f"{forbidden!r} logged by {record.name}"
