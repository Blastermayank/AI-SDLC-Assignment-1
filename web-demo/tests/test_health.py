"""GET /api/health (FR-004, FR-054; task T007)."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import BASE_URL, REPO_ROOT


def test_health_contract_shape(client):
    body = client.get("/api/health").json()
    assert set(body) == {"status", "server_instance", "repository_url", "part1a", "part1b"}
    assert body["status"] == "ok"
    assert body["part1a"] == {"available": True}
    assert set(body["part1b"]) == {"module_loaded", "configured", "model"}
    assert body["part1b"]["module_loaded"] is True
    assert body["part1b"]["model"] == "gemini-3.5-flash-lite"
    uuid.UUID(body["server_instance"])


def test_server_instance_is_stable_across_calls(client):
    first = client.get("/api/health").json()["server_instance"]
    assert client.get("/api/health").json()["server_instance"] == first


def test_configured_true_with_key_and_never_reveals_it(client, sentinel_key):
    response = client.get("/api/health")
    assert response.json()["part1b"]["configured"] is True
    assert sentinel_key not in response.text
    assert str(len(sentinel_key)) not in json.dumps(response.json()["part1b"])


def test_configured_false_without_key(client, no_key):
    assert client.get("/api/health").json()["part1b"]["configured"] is False


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (None, None),
        ("not a url", None),
        ("http://github.com/owner/repo", None),
        ("https://evil.example/owner/repo", None),
        ("https://github.com/owner/repo/extra/path", None),
        ("https://github.com/Blastermayank/Assignment-1", "https://github.com/Blastermayank/Assignment-1"),
    ],
)
def test_repository_url_validation(tmp_path, configured, expected):
    config_file = tmp_path / "portal-config.json"
    config_file.write_text(json.dumps({"repository_url": configured}), encoding="utf-8")
    settings = Settings.from_environment(repo_root=REPO_ROOT, config_file=config_file)
    with TestClient(create_app(settings), base_url=BASE_URL) as client:
        assert client.get("/api/health").json()["repository_url"] == expected


def test_missing_config_file_means_not_configured(tmp_path):
    settings = Settings.from_environment(
        repo_root=REPO_ROOT, config_file=tmp_path / "does-not-exist.json"
    )
    assert settings.repository_url is None
