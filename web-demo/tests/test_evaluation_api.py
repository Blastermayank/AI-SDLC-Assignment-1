"""Evaluation dashboard API (FR-030 to FR-033, SC-006; tasks T035, T036)."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, client_for

# Copy of Part-1B/evidence/eval-results.json at commit 2c88355 (saved 2026-11-06T06:19:02Z).
# Compared by canonical JSON content because checkouts may convert line endings.
FIXTURE = Path(__file__).parent / "fixtures" / "eval-results-reference-20261106T061902Z.json"
EVIDENCE = REPO_ROOT / "Part-1B" / "evidence"


def canonical_sha256(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    text = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture
def reference_repo(make_repo):
    """Temporary repository whose current report is the 86.7% reference report."""
    root = make_repo()
    shutil.copyfile(FIXTURE, root / "Part-1B" / "evidence" / "eval-results.json")
    return root


def test_fixture_is_the_reference_report():
    report = load(FIXTURE)
    assert report["timestamp_utc"].startswith("2026-11-06T06:19:02")
    archived = EVIDENCE / "eval-results-run-6-86.7pct.json"
    assert canonical_sha256(FIXTURE) == canonical_sha256(archived)


def test_current_report_is_served_unchanged(client):
    body = client.get("/api/part-1b/evaluation").json()
    assert body["report"] == load(EVIDENCE / "eval-results.json")
    assert body["source"] == "Part-1B/evidence/eval-results.json"
    assert body["is_current"] is True
    assert "passed cases / completed cases" in body["scoring"]["method"]


def test_reference_report_figures(reference_repo):
    with client_for(reference_repo) as client:
        body = client.get("/api/part-1b/evaluation").json()
    report = body["report"]
    assert report["model"] == "gemini-3.5-flash-lite"
    assert report["total_cases"] == 15
    assert report["completed_cases"] == 15
    assert report["passed_cases"] == 13
    assert report["aggregate_score"] == pytest.approx(86.6666, abs=1e-3)
    assert report["threshold"] == 80.0
    assert report["status"] == "PASS"
    failed = {result["id"]: result["error"] for result in report["results"] if not result["pass"]}
    assert set(failed) == {3, 8}
    assert failed[3].startswith("L3: Expected 'Cross-Site Scripting (XSS)'")
    assert failed[8].startswith("L3: Expected 'Insecure Configuration'")


def test_dataset_fields_are_joined_for_the_current_report(reference_repo):
    with client_for(reference_repo) as client:
        cases = {case["id"]: case for case in client.get("/api/part-1b/evaluation").json()["cases"]}
    assert cases[3]["expected_vuln"] == "Cross-Site Scripting (XSS)"
    assert cases[3]["input"] == "html = f'<div>{user_input}</div>'"
    assert cases[3]["type"] == "normal"
    assert cases[3]["expected_status"] == "success"


def test_earlier_report_can_be_viewed_without_dataset_join(client):
    body = client.get(
        "/api/part-1b/evaluation", params={"report": "eval-results-run-6-86.7pct.json"}
    ).json()
    assert body["is_current"] is False
    assert body["cases"] is None
    assert body["report"] == load(EVIDENCE / "eval-results-run-6-86.7pct.json")
    assert "dataset" in body["cases_note"]


@pytest.mark.parametrize(
    "name", ["../README.md", "eval-results-run-99-1.0pct.json", "dataset.json", "x.json"]
)
def test_unknown_or_unsafe_report_names_are_refused(client, name):
    response = client.get("/api/part-1b/evaluation", params={"report": name})
    assert response.status_code == 404
    assert response.json()["error"]["category"] == "not_found"


def test_history_lists_every_saved_report_in_time_order(client):
    body = client.get("/api/part-1b/evaluation/history").json()
    runs = body["runs"]
    files = sorted(p.name for p in EVIDENCE.glob("eval-results*.json"))
    assert sorted(run["file"].split("/")[-1] for run in runs) == files
    timestamps = [run["timestamp_utc"] for run in runs]
    assert timestamps == sorted(timestamps)
    assert sum(run["is_current"] for run in runs) == 1
    assert "not directly comparable" in body["caveat"]
    run6 = next(run for run in runs if run["file"].endswith("run-6-86.7pct.json"))
    assert run6["status"] == "PASS"
    assert run6["failed_case_ids"] == [3, 8]
    assert run6["interrupted_case_ids"] == []
    assert run6["aggregate_score"] == pytest.approx(86.6666, abs=1e-3)


def test_history_separates_interrupted_cases(client):
    runs = client.get("/api/part-1b/evaluation/history").json()["runs"]
    run7 = next(run for run in runs if run["file"].endswith("run-7-incomplete.json"))
    assert run7["status"] == "INCOMPLETE"
    assert run7["failed_case_ids"] == [3, 8]
    assert run7["interrupted_case_ids"] == [15]
    assert run7["service_error"] is True


def test_latest_completed_run_is_identified(client):
    body = client.get("/api/part-1b/evaluation/history").json()
    latest = body["latest_completed"]
    completed = [run for run in body["runs"] if run["status"] in {"PASS", "FAIL"}]
    assert latest["file"] == completed[-1]["file"]


def test_incomplete_report_with_more_cases_is_displayed_accurately(make_repo):
    root = make_repo()
    report = {
        "timestamp_utc": "2026-11-08T10:00:00+00:00", "model": "gemini-3.5-flash-lite",
        "threshold": 80.0, "total_cases": 16, "completed_cases": 4, "passed_cases": 4,
        "partial_score": 100.0, "aggregate_score": None, "status": "INCOMPLETE",
        "service_error": {"case_id": 5, "error_type": "ServerError", "details": "503"},
        "results": [{"id": i, "layer1": True, "layer2": True, "layer3": True, "pass": True,
                     "error": "", "model_output": {"status": "success", "findings": []}}
                    for i in range(1, 5)],
    }
    (root / "Part-1B" / "evidence" / "eval-results.json").write_text(json.dumps(report))
    with client_for(root) as client:
        body = client.get("/api/part-1b/evaluation").json()
    assert body["report"]["status"] == "INCOMPLETE"
    assert body["report"]["aggregate_score"] is None
    assert body["report"]["total_cases"] == 16
    assert len(body["cases"]) == 4


@pytest.mark.parametrize("content", [None, "{not json"])
def test_missing_or_invalid_report_is_unavailable(make_repo, content):
    root = make_repo()
    current = root / "Part-1B" / "evidence" / "eval-results.json"
    if content is None:
        current.unlink()
    else:
        current.write_text(content)
    with client_for(root) as client:
        response = client.get("/api/part-1b/evaluation")
    assert response.status_code == 404
    assert response.json()["error"]["category"] == "report_unavailable"


def test_unreadable_history_file_is_listed_not_dropped(make_repo):
    root = make_repo()
    (root / "Part-1B" / "evidence" / "eval-results-run-9-0.0pct.json").write_text("{broken")
    with client_for(root) as client:
        runs = client.get("/api/part-1b/evaluation/history").json()["runs"]
    broken = next(run for run in runs if run["file"].endswith("run-9-0.0pct.json"))
    assert broken["status"] == "UNREADABLE"


def _snapshot(folder):
    return {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in folder.rglob("*") if p.is_file()}


def test_dashboard_is_read_only_and_makes_no_model_call(client, sentinel_key, fake_gemini):
    calls = fake_gemini("{}")
    before = _snapshot(EVIDENCE)
    for _ in range(3):
        assert client.get("/api/part-1b/evaluation").status_code == 200
        assert client.get("/api/part-1b/evaluation/history").status_code == 200
    assert _snapshot(EVIDENCE) == before
    assert calls.calls == []
