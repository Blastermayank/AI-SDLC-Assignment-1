"""Part 1B evaluation dashboard API (FR-030 to FR-033; research R13; task T038).

Read-only: saved reports and the dataset are read and passed through unchanged. No model
call is made and no file is written. Dataset inputs are joined only to the current report,
because earlier runs may have used an earlier version of the dataset.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Request

from app.config import Settings
from app.errors import PortalError

router = APIRouter()

CURRENT_NAME = "eval-results.json"
REPORT_NAME = re.compile(r"^eval-results(-run-\d+-[A-Za-z0-9.]+)?\.json$")
COMPLETED = ("PASS", "FAIL")

CAVEAT = (
    "Dataset inputs, the reviewer prompt and the evaluator's category aliases changed between "
    "runs, so scores are not directly comparable. Reports since 2026-11-07 record a dataset "
    "fingerprint."
)
SCORING = {
    "method": "aggregate score = passed cases / completed cases x 100",
    "pass_rule": "PASS only when every case completed and the score is at least the threshold",
    "incomplete_rule": (
        "INCOMPLETE when a Gemini service or execution error stopped the run; no final score"
    ),
}
EARLIER_CASES_NOTE = (
    "Case inputs and expected categories are shown only for the current report, because "
    "earlier runs may have used an earlier version of the dataset."
)


def _read_report(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(report, dict) or not isinstance(report.get("results"), list):
        raise ValueError("not an evaluation report")
    return report


def _report_files(evidence_dir: Path) -> list[Path]:
    if not evidence_dir.is_dir():
        return []
    return sorted(
        path
        for path in evidence_dir.glob("eval-results*.json")
        if path.is_file() and REPORT_NAME.match(path.name)
    )


def _dataset_cases(dataset_file: Path, report: dict) -> list[dict] | None:
    try:
        dataset = json.loads(dataset_file.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(dataset, list):
        return None
    by_id = {case.get("id"): case for case in dataset if isinstance(case, dict)}
    cases = []
    for result in report["results"]:
        case = by_id.get(result.get("id"))
        if case is not None:
            cases.append(
                {
                    "id": case.get("id"),
                    "type": case.get("type"),
                    "input": case.get("input"),
                    "expected_vuln": case.get("expected_vuln"),
                    "expected_status": case.get("expected_status", "success"),
                }
            )
    return cases


def _summarize(path: Path, settings: Settings) -> dict:
    entry = {"file": settings.relative(path), "is_current": path.name == CURRENT_NAME}
    try:
        report = _read_report(path)
    except (OSError, ValueError):
        return {**entry, "status": "UNREADABLE", "timestamp_utc": None}

    results = report["results"]
    interrupted = [
        r.get("id") for r in results if r.get("service_error") or r.get("execution_error")
    ]
    failed = [r.get("id") for r in results if not r.get("pass") and r.get("id") not in interrupted]
    return {
        **entry,
        "timestamp_utc": report.get("timestamp_utc"),
        "total_cases": report.get("total_cases"),
        "completed_cases": report.get("completed_cases"),
        "passed_cases": report.get("passed_cases"),
        "aggregate_score": report.get("aggregate_score"),
        "partial_score": report.get("partial_score"),
        "status": report.get("status"),
        "failed_case_ids": failed,
        "interrupted_case_ids": interrupted,
        "service_error": bool(report.get("service_error")),
        "dataset_sha256": report.get("dataset_sha256"),
    }


@router.get("/api/part-1b/evaluation")
async def evaluation(request: Request, report: str | None = None) -> dict:
    settings: Settings = request.app.state.settings
    name = report or CURRENT_NAME
    if not REPORT_NAME.match(name):
        raise PortalError("not_found")
    is_current = name == CURRENT_NAME
    path = settings.part1b_evidence_dir / name
    if not path.is_file():
        raise PortalError("report_unavailable" if is_current else "not_found")
    try:
        data = _read_report(path)
    except (OSError, ValueError):
        raise PortalError("report_unavailable") from None

    return {
        "source": settings.relative(path),
        "file": name,
        "is_current": is_current,
        "report": data,
        "cases": _dataset_cases(settings.dataset_file, data) if is_current else None,
        "cases_note": None if is_current else EARLIER_CASES_NOTE,
        "dataset_source": settings.relative(settings.dataset_file),
        "scoring": SCORING,
    }


@router.get("/api/part-1b/evaluation/history")
async def history(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    runs = [_summarize(path, settings) for path in _report_files(settings.part1b_evidence_dir)]
    runs.sort(
        key=lambda run: (run["timestamp_utc"] is None, run["timestamp_utc"] or "", run["file"])
    )
    completed = [run for run in runs if run["status"] in COMPLETED]
    return {
        "caveat": CAVEAT,
        "runs": runs,
        "latest_completed": completed[-1] if completed else None,
    }
