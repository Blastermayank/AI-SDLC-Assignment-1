"""Read saved harness runs (contracts/consumed-files.md; FR-017; task T025).

Only files named in a run's summary.json and located inside that run folder are read.
The portal never runs a harness.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RUN_NAME = re.compile(r"^\d{8}-\d{6}$")


def _read_summary(run_dir: Path, max_bytes: int) -> dict | None:
    summary_file = run_dir / "summary.json"
    if not summary_file.is_file() or summary_file.stat().st_size > max_bytes:
        return None
    try:
        summary = json.loads(summary_file.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(summary, dict) or not isinstance(summary.get("gates"), list):
        return None
    return summary


def _read_transcripts(run_dir: Path, summary: dict, max_bytes: int) -> dict[str, str]:
    transcripts: dict[str, str] = {}
    root = run_dir.resolve()
    for gate in summary["gates"]:
        if not isinstance(gate, dict) or not isinstance(gate.get("transcript"), str):
            continue
        candidate = (run_dir / gate["transcript"]).resolve()
        if candidate.parent != root or not candidate.is_file():
            continue
        if candidate.stat().st_size > max_bytes:
            continue
        name = str(gate.get("name") or gate["transcript"])
        transcripts[name] = candidate.read_text(encoding="utf-8", errors="replace")
    return transcripts


def latest_run(results_dir: Path, max_bytes: int) -> dict:
    """Latest valid run with transcripts, plus a newest-first history of all valid runs."""
    if not results_dir.is_dir():
        return {"available": False, "history": []}

    runs = sorted(
        (path for path in results_dir.iterdir() if path.is_dir() and RUN_NAME.match(path.name)),
        key=lambda path: path.name,
        reverse=True,
    )
    valid = [
        (run_dir, summary) for run_dir in runs if (summary := _read_summary(run_dir, max_bytes))
    ]
    history = [
        {
            "run": run_dir.name,
            "timestamp_utc": summary.get("timestamp_utc"),
            "result": summary.get("result"),
        }
        for run_dir, summary in valid
    ]
    if not valid:
        return {"available": False, "history": []}

    run_dir, summary = valid[0]
    return {
        "available": True,
        "run": run_dir.name,
        "summary": summary,
        "transcripts": _read_transcripts(run_dir, summary, max_bytes),
        "history": history,
    }
