"""Specification-derived unit tests for the Part 1B reviewer and evaluation harness.

Added 2026-11-07 (change cycle: change-cycles/2026-11-07-missing-input-case).
Requirement IDs refer to speckit.specify.md. No test makes a network call.

Run from the Part-1B directory:  python -m pytest tests -v
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATASET_FILE = PROJECT_DIR / "evals" / "dataset.json"
ORIGINAL_DATASET = Path(__file__).resolve().parent / "fixtures" / "dataset-2c88355.json"


def _load_evaluate():
    spec = importlib.util.spec_from_file_location(
        "part1b_evaluate", PROJECT_DIR / ".harness" / "evaluate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluate = _load_evaluate()
reviewer = sys.modules["reviewer"]  # imported by evaluate.py

SOURCE = "query = f'SELECT * FROM users WHERE id = {user_id}'"


def _finding(**overrides):
    finding = {
        "vulnerability": "SQL Injection",
        "severity": "High",
        "description": "User input is interpolated into SQL.",
        "evidence": "SELECT * FROM users WHERE id = {user_id}",
        "remediation": "Use parameterised queries.",
    }
    finding.update(overrides)
    return finding


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --- Layer 2: invariants (Section 4) -----------------------------------------


def test_valid_success_response_has_no_invariant_violations():
    output = {"status": "success", "findings": [_finding()]}
    assert evaluate.invariant_check(output, SOURCE) == []


def test_inv8_default_expected_status_is_success():
    output = {"status": "error", "findings": []}
    assert evaluate.invariant_check(output, SOURCE) == [
        "Expected status 'success', received 'error'."
    ]


def test_inv8_expected_error_status_accepts_error_response():
    output = {"status": "error", "findings": []}
    assert evaluate.invariant_check(output, "   ", expected_status="error") == []


def test_inv8_expected_error_status_rejects_success_response():
    output = {"status": "success", "findings": []}
    assert evaluate.invariant_check(output, "   ", expected_status="error") == [
        "Expected status 'error', received 'success'."
    ]


def test_inv3_error_response_must_not_contain_findings():
    output = {"status": "error", "findings": [_finding()]}
    errors = evaluate.invariant_check(output, SOURCE, expected_status="error")
    assert "Error status must not contain findings." in errors


def test_inv4_invalid_severity_is_reported():
    output = {"status": "success", "findings": [_finding(severity="Critical")]}
    assert "Finding 1: invalid severity." in evaluate.invariant_check(output, SOURCE)


def test_inv6_evidence_must_be_an_exact_source_excerpt():
    output = {"status": "success", "findings": [_finding(evidence="not in the source")]}
    assert "Finding 1: evidence is not an exact source excerpt." in evaluate.invariant_check(
        output, SOURCE
    )


def test_inv7_more_than_ten_findings_is_reported():
    output = {"status": "success", "findings": [_finding() for _ in range(11)]}
    assert "More than 10 findings returned." in evaluate.invariant_check(output, SOURCE)


# --- Layer 3: semantic checks (Section 5) ------------------------------------


def test_sem1_sem2_alias_matches_expected_category():
    assert evaluate.semantic_check("Code Injection", [{"vulnerability": "Remote Code Execution"}])


def test_sem1_unrelated_category_does_not_match():
    assert not evaluate.semantic_check("SQL Injection", [{"vulnerability": "Cross-Site Scripting"}])


def test_sem3_negative_case_requires_empty_findings():
    assert evaluate.semantic_check("None", [])
    assert not evaluate.semantic_check("None", [{"vulnerability": "Unsafe File Write"}])


# --- Section 2: input requirements -------------------------------------------


@pytest.mark.parametrize("blank", ["", "   ", "   \n\t  "])
def test_blank_input_returns_error_response_without_model_call(blank, monkeypatch):
    # With no key and no cached client, any attempt to call Gemini would raise.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(reviewer, "_client", None)
    assert json.loads(reviewer.analyze_code(blank)) == {"status": "error", "findings": []}


# --- Section 7: report traceability and preservation -------------------------


def test_dataset_fingerprint_is_sha256_of_canonical_json():
    canonical = json.dumps(
        _load_json(DATASET_FILE), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert evaluate.dataset_fingerprint(DATASET_FILE) == expected


def test_dataset_fingerprint_ignores_line_endings_and_bom(tmp_path):
    text = DATASET_FILE.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    lf_file = tmp_path / "lf.json"
    crlf_bom_file = tmp_path / "crlf_bom.json"
    lf_file.write_bytes(text.encode("utf-8"))
    crlf_bom_file.write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))
    assert evaluate.dataset_fingerprint(lf_file) == evaluate.dataset_fingerprint(crlf_bom_file)


def test_archive_copies_current_report_to_next_run_number(tmp_path):
    (tmp_path / "eval-results-run-5-86.7pct.json").write_text("{}", encoding="utf-8")
    current = tmp_path / "eval-results.json"
    current.write_bytes(b'{"aggregate_score": 86.66666666666667, "status": "PASS"}')

    archived = evaluate.archive_existing_report(current)

    assert archived.name == "eval-results-run-6-86.7pct.json"
    assert archived.read_bytes() == current.read_bytes()


def test_archive_skips_when_an_identical_archive_exists(tmp_path):
    content = b'{"aggregate_score": 86.66666666666667, "status": "PASS"}'
    (tmp_path / "eval-results-run-6-86.7pct.json").write_bytes(content)
    current = tmp_path / "eval-results.json"
    current.write_bytes(content)

    assert evaluate.archive_existing_report(current) is None
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "eval-results-run-6-86.7pct.json",
        "eval-results.json",
    ]


def test_archive_names_incomplete_reports(tmp_path):
    current = tmp_path / "eval-results.json"
    current.write_bytes(b'{"aggregate_score": null, "status": "INCOMPLETE"}')

    archived = evaluate.archive_existing_report(current)

    assert archived.name == "eval-results-run-1-incomplete.json"


def test_archive_does_nothing_without_a_current_report(tmp_path):
    assert evaluate.archive_existing_report(tmp_path / "eval-results.json") is None


# --- Section 6: evaluation dataset -------------------------------------------


def test_dataset_cases_have_required_fields_and_unique_ids():
    cases = _load_json(DATASET_FILE)
    ids = [case["id"] for case in cases]
    assert len(cases) >= 15
    assert len(ids) == len(set(ids))
    for case in cases:
        assert {"id", "type", "input", "expected_vuln"} <= case.keys()
        assert case.get("expected_status", "success") in {"success", "error"}


def test_dataset_covers_missing_mandatory_information():
    missing = [case for case in _load_json(DATASET_FILE) if case["type"] == "missing"]
    assert missing, "No missing-mandatory-information case in the dataset."
    for case in missing:
        assert case["input"].strip() == ""
        assert case["expected_status"] == "error"
        assert case["expected_vuln"] == "None"


def test_original_cases_are_unchanged():
    current = {case["id"]: case for case in _load_json(DATASET_FILE)}
    for case in _load_json(ORIGINAL_DATASET):
        assert current.get(case["id"]) == case, f"Case {case['id']} differs from commit 2c88355"
