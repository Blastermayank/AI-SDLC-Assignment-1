"""Part 1B analysis through the real reviewer with Gemini faked at the SDK boundary.

FR-020 to FR-028, FR-024, research R5-R8; task T029.
"""

import asyncio
import json
import logging
import os
import threading

import httpx
import pytest
from fastapi.testclient import TestClient
from google.genai import errors

from app.config import Settings
from app.main import create_app
from tests.conftest import BASE_URL, REPO_ROOT

CODE = "query = f'SELECT * FROM users WHERE id = {user_id}'"
FINDING = {
    "vulnerability": "SQL Injection",
    "severity": "High",
    "description": "User input is interpolated into a SQL statement.",
    "evidence": "SELECT * FROM users WHERE id = {user_id}",
    "remediation": "Use parameterised queries.",
}
GOOD = {"status": "success", "findings": [FINDING]}
SDK_TEXT = "SDK-INTERNAL-DETAIL"


def analyze(client, code=CODE):
    return client.post("/api/part-1b/analyze", json={"code": code})


def api_error(cls, code, status):
    return cls(code, {"error": {"code": code, "status": status, "message": SDK_TEXT}})


def test_successful_analysis_returns_findings_and_live_checks(
    client, app, sentinel_key, fake_gemini
):
    calls = fake_gemini(json.dumps(GOOD))
    response = analyze(client)

    assert response.status_code == 200
    body = response.json()
    model = app.state.backends.evaluate_module.MODEL
    assert body["model"] == model
    assert isinstance(body["elapsed_ms"], int)
    assert body["result"] == GOOD
    assert json.loads(body["raw"]) == body["result"]
    assert body["live_checks"]["layer1"] == {"passed": True, "errors": []}
    assert body["live_checks"]["layer2"] == {"passed": True, "errors": []}
    assert body["live_checks"]["layer3"]["applicable"] is False
    assert len(calls.calls) == 1
    assert calls.calls[0]["model"] == model
    assert CODE in calls.calls[0]["contents"]
    assert sentinel_key not in response.text


def test_layer2_reports_fabricated_evidence(client, sentinel_key, fake_gemini):
    fabricated = {"status": "success", "findings": [dict(FINDING, evidence="not in the code")]}
    fake_gemini(json.dumps(fabricated))
    body = analyze(client).json()
    assert body["live_checks"]["layer1"]["passed"] is True
    assert body["live_checks"]["layer2"] == {
        "passed": False,
        "errors": ["Finding 1: evidence is not an exact source excerpt."],
    }


def test_no_findings_is_a_completed_analysis(client, sentinel_key, fake_gemini):
    fake_gemini(json.dumps({"status": "success", "findings": []}))
    response = analyze(client, "def add(a, b):\n    return a + b")
    assert response.status_code == 200
    assert response.json()["result"]["findings"] == []
    assert response.json()["live_checks"]["layer2"]["passed"] is True


@pytest.mark.parametrize("code", ["", "   ", "   \n\t  ", "x" * 20_001])
def test_invalid_code_is_refused_without_a_model_call(client, sentinel_key, fake_gemini, code):
    calls = fake_gemini(json.dumps(GOOD))
    response = analyze(client, code)
    assert response.status_code == 422
    assert response.json()["error"]["category"] == "invalid_input"
    assert calls.calls == []


def test_missing_key_is_reported_without_a_model_call(client, no_key, fake_gemini):
    calls = fake_gemini(json.dumps(GOOD))
    response = analyze(client)
    assert response.status_code == 503
    assert response.json()["error"]["category"] == "not_configured"
    assert calls.calls == []


@pytest.mark.parametrize(
    "case",
    [
        (api_error(errors.ClientError, 429, "RESOURCE_EXHAUSTED"), 429, "quota"),
        (api_error(errors.ClientError, 401, "UNAUTHENTICATED"), 503, "not_configured"),
        (api_error(errors.ClientError, 403, "PERMISSION_DENIED"), 503, "not_configured"),
        (api_error(errors.ClientError, 400, "INVALID_ARGUMENT"), 502, "service_error"),
        (api_error(errors.ServerError, 503, "UNAVAILABLE"), 502, "service_error"),
        (httpx.ConnectError(f"connection refused {SDK_TEXT}"), 504, "network_timeout"),
        ("not json at all", 502, "invalid_model_output"),
        ("", 502, "invalid_model_output"),
        (
            json.dumps({"status": "success", "findings": [dict(FINDING, severity="Critical")]}),
            502,
            "invalid_model_output",
        ),
    ],
)
def test_failures_are_classified_and_safe(client, sentinel_key, fake_gemini, case):
    behaviour, status, category = case
    fake_gemini(behaviour)
    response = analyze(client)
    assert response.status_code == status
    assert response.json()["error"]["category"] == category
    assert SDK_TEXT not in response.text
    assert sentinel_key not in response.text
    assert "findings" not in response.json()


def test_slow_model_ends_with_timeout(sentinel_key, fake_gemini):
    fake_gemini(json.dumps(GOOD), delay=1.0)
    settings = Settings.from_environment(repo_root=REPO_ROOT, analysis_timeout_s=0.2)
    with TestClient(create_app(settings), base_url=BASE_URL) as client:
        response = analyze(client)
    assert response.status_code == 504
    assert response.json()["error"]["category"] == "network_timeout"


def test_second_analysis_while_one_runs_is_refused(client, app, sentinel_key, fake_gemini):
    calls = fake_gemini(json.dumps(GOOD))
    # Hold the app's real lock. asyncio.run() runs in a helper thread because a browser test
    # earlier in the same pytest process may leave an event loop on the main thread.
    holder = threading.Thread(target=asyncio.run, args=(app.state.analysis_lock.acquire(),))
    holder.start()
    holder.join()
    assert app.state.analysis_lock.locked()
    response = analyze(client)
    assert response.status_code == 409
    assert response.json()["error"]["category"] == "busy"
    assert calls.calls == []


def test_model_markup_is_returned_verbatim_for_text_rendering(client, sentinel_key, fake_gemini):
    markup = "<img src=x onerror=alert(1)>"
    fake_gemini(json.dumps({"status": "success", "findings": [dict(FINDING, description=markup)]}))
    assert analyze(client).json()["result"]["findings"][0]["description"] == markup


def _file_listing(root):
    skip = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".git"}
    listing = set()
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        listing.update(os.path.join(current, name) for name in files)
    return listing


def test_submitted_code_is_not_stored_or_logged(client, sentinel_key, fake_gemini, caplog):
    marker = "FR024-CODE-MARKER-5b1e"
    fake_gemini(json.dumps({"status": "success", "findings": []}))
    before = _file_listing(REPO_ROOT)
    with caplog.at_level(logging.DEBUG):
        response = analyze(client, f"secret_marker = '{marker}'")
    assert response.status_code == 200
    assert _file_listing(REPO_ROOT) == before
    assert all(marker not in record.getMessage() for record in caplog.records)
