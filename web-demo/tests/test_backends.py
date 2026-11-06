"""Loading Part 1A and Part 1B by file path (research R3; task T009)."""

import sys

import pytest

from app.backends import BackendLoadError, load_backends
from app.config import Settings
from tests.conftest import REPO_ROOT


def test_backends_load_under_unique_module_names():
    backends = load_backends(Settings.from_environment(repo_root=REPO_ROOT))
    assert backends.limiter_module.__name__ == "part1a_limiter"
    assert backends.evaluate_module.__name__ == "part1b_evaluate"
    assert backends.reviewer_module is sys.modules["reviewer"]
    assert backends.evaluate_module.analyze_code is sys.modules["reviewer"].analyze_code


def test_loading_writes_no_bytecode_under_part_folders(make_repo):
    root = make_repo()
    load_backends(Settings.from_environment(repo_root=root))
    written = list((root / "Part-1A").rglob("__pycache__"))
    written += list((root / "Part-1B").rglob("__pycache__"))
    assert written == []


def test_missing_backend_raises_clear_error(make_repo):
    root = make_repo()
    (root / "Part-1A" / "src" / "limiter.py").unlink()
    with pytest.raises(BackendLoadError, match=r"limiter\.py"):
        load_backends(Settings.from_environment(repo_root=root))
