"""Evidence index and viewer API (FR-040, FR-041; research R15; task T046)."""

import hashlib

import pytest

from tests.conftest import REPO_ROOT, client_for


def all_items(body):
    return [item for group in body["groups"] for item in group["items"]]


def test_groups_are_present(client):
    groups = {group["group"]: group for group in client.get("/api/evidence").json()["groups"]}
    assert set(groups) == {"historical", "portal", "verification"}
    for group in groups.values():
        assert group["title"]
        assert group["items"]


def test_key_artifacts_are_listed(client):
    ids = {item["id"] for item in all_items(client.get("/api/evidence").json())}
    for expected in (
        "1a-spec", "1a-src", "1a-tests", "1a-harness", "1a-initial", "1a-final",
        "1b-spec", "1b-src", "1b-evaluator", "1b-dataset", "1b-initial", "1b-final",
        "1b-report-eval-results-json", "portal-spec", "portal-constitution",
    ):
        assert expected in ids


def test_every_listed_item_is_byte_identical(client):
    for item in all_items(client.get("/api/evidence").json()):
        raw = (REPO_ROOT / item["path"]).read_bytes()
        body = client.get(f"/api/evidence/{item['id']}").json()
        assert body["content"].encode("utf-8") == raw, item["path"]
        assert body["sha256"] == hashlib.sha256(raw).hexdigest()
        assert body["size_bytes"] == len(raw) == item["size_bytes"]
        assert body["path"] == item["path"]


def test_only_existing_files_are_listed(make_repo):
    root = make_repo()
    (root / "Part-1A" / "harness-log.md").unlink()
    with client_for(root) as client:
        ids = {item["id"] for item in all_items(client.get("/api/evidence").json())}
    assert "1a-harness-log" not in ids
    assert "1a-src" in ids
    assert "1a-plan" not in ids  # Part 1A has no speckit.plan.md


def test_oversized_and_non_utf8_files_are_not_listed(make_repo):
    root = make_repo()
    folder = root / "Part-1B" / "evidence" / "unit-test-results"
    (folder / "big-pytest.txt").write_bytes(b"x" * 1_048_577)
    (folder / "binary-pytest.txt").write_bytes(b"\xff\xfe\x00not text")
    with client_for(root) as client:
        paths = {item["path"] for item in all_items(client.get("/api/evidence").json())}
    assert "Part-1B/evidence/unit-test-results/big-pytest.txt" not in paths
    assert "Part-1B/evidence/unit-test-results/binary-pytest.txt" not in paths


def test_unknown_id_is_not_found(client):
    response = client.get("/api/evidence/no-such-item")
    assert response.status_code == 404
    assert response.json()["error"]["category"] == "not_found"


@pytest.mark.parametrize(
    "item_id",
    [
        "../README.md", "..%2F..%2FREADME.md", "%2e%2e", "C:/Windows/win.ini",
        "Part-1A/src/limiter.py", "..", "1A-SRC",
    ],
)
def test_path_like_ids_never_resolve(client, item_id):
    response = client.get(f"/api/evidence/{item_id}")
    assert response.status_code == 404
    assert "def check_request" not in response.text


def test_file_deleted_after_listing_is_not_found(make_repo):
    root = make_repo()
    with client_for(root) as client:
        assert client.get("/api/evidence/1a-tests").status_code == 200
        (root / "Part-1A" / "tests" / "test_limiter.py").unlink()
        assert client.get("/api/evidence/1a-tests").status_code == 404
