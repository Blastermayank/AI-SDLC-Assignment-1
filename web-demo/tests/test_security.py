"""Web security controls from research R9 (FR-051, FR-052; task T008)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.security import CONTENT_SECURITY_POLICY
from tests.conftest import BASE_URL

EXPECTED_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'none'"
)


def test_csp_constant_matches_research_r9():
    assert CONTENT_SECURITY_POLICY == EXPECTED_CSP


@pytest.mark.parametrize("path", ["/", "/api/health", "/static/js/app.js", "/no-such-page"])
def test_security_headers_on_every_response(client, path):
    headers = client.get(path).headers
    assert headers["content-security-policy"] == EXPECTED_CSP
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["x-frame-options"] == "DENY"


def test_api_responses_are_not_cached(client):
    assert client.get("/api/health").headers["cache-control"] == "no-store"


def test_javascript_served_as_javascript(client):
    assert client.get("/static/js/app.js").headers["content-type"].startswith("text/javascript")


def test_foreign_host_header_is_rejected(client):
    assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 400


def test_cross_origin_post_is_rejected(client):
    response = client.post("/api/part-1a/reset", headers={"origin": "http://evil.example"})
    assert response.status_code == 403
    assert response.json()["error"]["category"] == "forbidden_origin"


def test_same_origin_post_is_allowed(client):
    response = client.post("/api/part-1a/reset", headers={"origin": BASE_URL})
    assert response.status_code == 200


def test_oversized_body_is_rejected(client):
    body = json.dumps({"code": "x" * 70_000})
    response = client.post(
        "/api/part-1b/analyze", content=body, headers={"content-type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["error"]["category"] == "payload_too_large"


@pytest.mark.parametrize(
    ("path", "payload", "marker"),
    [
        ("/api/part-1b/analyze", {"code": "ECHO-MARKER-" * 2_000}, "ECHO-MARKER"),
        ("/api/part-1a/request", {"client_id": "bad id ECHO-MARK!", "tier": "free"}, "ECHO-MARK"),
        ("/api/part-1a/request", {"client_id": "ok", "tier": "ECHO-TIER"}, "ECHO-TIER"),
    ],
)
def test_validation_errors_never_echo_input(client, path, payload, marker):
    response = client.post(path, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["category"] == "invalid_input"
    assert marker not in response.text


def test_unexpected_errors_return_safe_envelope(app):
    async def boom():
        raise RuntimeError("SECRET-TRACE-MARKER")

    app.add_api_route("/api/test-boom", boom)
    with TestClient(app, base_url=BASE_URL, raise_server_exceptions=False) as client:
        response = client.get("/api/test-boom")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"category": "internal_error", "message": "Unexpected server error."}
    }
    assert "Traceback" not in response.text
    assert "SECRET-TRACE-MARKER" not in response.text
    assert response.headers["content-security-policy"] == EXPECTED_CSP


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_third_party_documentation_pages_are_disabled(client, path):
    assert client.get(path).status_code == 404


def test_openapi_document_is_available(client):
    assert client.get("/api/openapi.json").status_code == 200


def test_unknown_api_path_uses_error_envelope(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["category"] == "not_found"
