"""Shared fixtures for the web-demo test suite (task T006).

Safety: every test runs with GEMINI_API_KEY removed and a reviewer client that refuses
network use, so no test can make a live Gemini call by accident. Tests that need model
output install a fake client with the `fake_gemini` fixture (research R8).
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.backends import load_backends
from app.config import Settings
from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "http://127.0.0.1:8000"
SENTINEL_KEY = "SENTINEL-7d41b0c9-must-never-appear"

_COPY_IGNORE = shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache", ".ruff_cache")


class NoNetworkClient:
    """Stands in for the Gemini SDK client when a test did not install a fake."""

    class _Models:
        def generate_content(self, **_kwargs):
            raise AssertionError("Unexpected Gemini call: install a fake with fake_gemini().")

    def __init__(self) -> None:
        self.models = self._Models()


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeModels:
    """Records calls and returns canned text or raises a supplied exception."""

    def __init__(self, behaviour, delay: float = 0.0) -> None:
        self.behaviour = behaviour
        self.delay = delay
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay:
            time.sleep(self.delay)
        if isinstance(self.behaviour, BaseException):
            raise self.behaviour
        return FakeResponse(self.behaviour)


class FakeClient:
    def __init__(self, behaviour, delay: float = 0.0) -> None:
        self.models = FakeModels(behaviour, delay)


def reviewer_module():
    """The Part 1B reviewer module, loaded through the portal's backend loader."""
    load_backends(Settings.from_environment(repo_root=REPO_ROOT))
    return sys.modules["reviewer"]


@pytest.fixture(autouse=True)
def _isolate_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(reviewer_module(), "_client", NoNetworkClient())


@pytest.fixture
def sentinel_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", SENTINEL_KEY)
    return SENTINEL_KEY


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture
def fake_gemini(monkeypatch):
    """Install a fake SDK client at the network boundary; returns its recorder."""

    def install(behaviour, delay: float = 0.0) -> FakeModels:
        client = FakeClient(behaviour, delay)
        monkeypatch.setattr(reviewer_module(), "_client", client)
        return client.models

    return install


@pytest.fixture
def settings():
    return Settings.from_environment(repo_root=REPO_ROOT)


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app, base_url=BASE_URL) as test_client:
        yield test_client


@pytest.fixture
def make_repo(tmp_path):
    """Copy the parts of the repository the portal reads into a temporary root."""

    def build() -> Path:
        root = tmp_path / "repo"
        root.mkdir()
        for name in ("Part-1A", "Part-1B"):
            shutil.copytree(REPO_ROOT / name, root / name, ignore=_COPY_IGNORE)
        (root / "web-demo").mkdir()
        shutil.copytree(REPO_ROOT / "web-demo" / "specs", root / "web-demo" / "specs")
        memory = root / "web-demo" / ".specify" / "memory"
        memory.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "web-demo" / ".specify" / "memory" / "constitution.md", memory)
        shutil.copy2(REPO_ROOT / "README.md", root / "README.md")
        return root

    return build


def client_for(repo_root: Path, **overrides) -> TestClient:
    return TestClient(
        create_app(Settings.from_environment(repo_root=repo_root, **overrides)), base_url=BASE_URL
    )
