"""Evidence allow-list (FR-040, FR-041; research R15; task T048).

Files are served only by opaque IDs from this list, so a client can never name a path.
Only existing UTF-8 files up to the size limit are listed. Optional entries (for example a
Spec Kit plan that does not exist) are simply omitted when absent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

GROUP_TITLES = {
    "historical": "Assignment evidence: Part 1A and Part 1B",
    "portal": "Web portal specification artifacts",
    "verification": "Verification results: saved harness and test runs",
}
ID_PATTERN = re.compile(r"^[a-z0-9-]{1,200}$")


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    label: str
    group: str
    part: str
    path: str  # repository-relative, forward slashes


def _item(item_id: str, label: str, group: str, part: str, path: str) -> EvidenceItem:
    return EvidenceItem(item_id, label, group, part, path)


_A = "Part-1A"
_B = "Part-1B"
_CYCLE_A = f"{_A}/change-cycles/2026-11-07-ac3-retry-after"
_CYCLE_B = f"{_B}/change-cycles/2026-11-07-missing-input-case"
_SPECS = "web-demo/specs/001-web-demo-portal"

EXPLICIT: tuple[EvidenceItem, ...] = (
    _item("repo-readme", "Repository README", "historical", "repository", "README.md"),
    # Part 1A
    _item("1a-constitution", "Constitution", "historical", "1A", f"{_A}/speckit.constitution.md"),
    _item("1a-spec", "Specification (with clarifications)", "historical", "1A",
          f"{_A}/speckit.specify.md"),
    _item("1a-clarify", "Clarifications", "historical", "1A", f"{_A}/speckit.clarify.md"),
    _item("1a-plan", "Plan", "historical", "1A", f"{_A}/speckit.plan.md"),
    _item("1a-tasks", "Tasks", "historical", "1A", f"{_A}/speckit.tasks.md"),
    _item("1a-analyze", "Analysis report", "historical", "1A", f"{_A}/speckit.analyze.md"),
    _item("1a-cycle-plan", "Change-cycle plan (2026-11-07, AC3)", "historical", "1A",
          f"{_CYCLE_A}/plan.md"),
    _item("1a-cycle-tasks", "Change-cycle tasks (2026-11-07, AC3)", "historical", "1A",
          f"{_CYCLE_A}/tasks.md"),
    _item("1a-src", "Implementation: limiter.py", "historical", "1A", f"{_A}/src/limiter.py"),
    _item("1a-tests", "Tests: test_limiter.py", "historical", "1A", f"{_A}/tests/test_limiter.py"),
    _item("1a-harness", "Harness runner: run.ps1", "historical", "1A", f"{_A}/.harness/run.ps1"),
    _item("1a-requirements", "Pinned requirements", "historical", "1A", f"{_A}/requirements.txt"),
    _item("1a-harness-log", "Harness log (written by the student)", "historical", "1A",
          f"{_A}/harness-log.md"),
    _item("1a-initial", "Snapshot: initial generation", "historical", "1A",
          f"{_A}/evidence/initial-generation/limiter_initial.py"),
    _item("1a-final", "Snapshot: final generation (2026-11-05)", "historical", "1A",
          f"{_A}/evidence/final-generation/limiter_final.py"),
    _item("1a-final-ac3", "Snapshot: after AC3 repair (2026-11-07)", "historical", "1A",
          f"{_A}/evidence/final-generation/limiter_final_after_ac3_repair.py"),
    _item("1a-evidence-readme", "Evidence index", "historical", "1A", f"{_A}/evidence/README.md"),
    # Part 1B
    _item("1b-constitution", "Constitution", "historical", "1B", f"{_B}/speckit.constitution.md"),
    _item("1b-spec", "Specification (with clarifications)", "historical", "1B",
          f"{_B}/speckit.specify.md"),
    _item("1b-clarify", "Clarifications", "historical", "1B", f"{_B}/speckit.clarify.md"),
    _item("1b-plan", "Plan", "historical", "1B", f"{_B}/speckit.plan.md"),
    _item("1b-tasks", "Tasks", "historical", "1B", f"{_B}/speckit.tasks.md"),
    _item("1b-analyze", "Analysis report", "historical", "1B", f"{_B}/speckit.analyze.md"),
    _item("1b-cycle-plan", "Change-cycle plan (2026-11-07, missing input)", "historical", "1B",
          f"{_CYCLE_B}/plan.md"),
    _item("1b-cycle-tasks", "Change-cycle tasks (2026-11-07, missing input)", "historical", "1B",
          f"{_CYCLE_B}/tasks.md"),
    _item("1b-src", "Implementation: reviewer.py", "historical", "1B", f"{_B}/src/reviewer.py"),
    _item("1b-evaluator", "Evaluation harness: evaluate.py", "historical", "1B",
          f"{_B}/.harness/evaluate.py"),
    _item("1b-dataset", "Evaluation dataset", "historical", "1B", f"{_B}/evals/dataset.json"),
    _item("1b-tests", "Unit tests: test_evaluator.py", "historical", "1B",
          f"{_B}/tests/test_evaluator.py"),
    _item("1b-requirements", "Pinned requirements", "historical", "1B", f"{_B}/requirements.txt"),
    _item("1b-harness-log", "Harness log (written by the student)", "historical", "1B",
          f"{_B}/harness-log.md"),
    _item("1b-initial", "Snapshot: initial generation", "historical", "1B",
          f"{_B}/evidence/initial-generation/reviewer_initial.py"),
    _item("1b-final", "Snapshot: final generation", "historical", "1B",
          f"{_B}/evidence/final-generation/reviewer_final.py"),
    _item("1b-dataset-before", "Dataset before security refinement", "historical", "1B",
          f"{_B}/evidence/dataset-before-security-refinement.json"),
    _item("1b-evidence-readme", "Evidence index", "historical", "1B", f"{_B}/evidence/README.md"),
    # Portal
    _item("portal-constitution", "Portal constitution", "portal", "portal",
          "web-demo/.specify/memory/constitution.md"),
    _item("portal-spec", "Specification", "portal", "portal", f"{_SPECS}/spec.md"),
    _item("portal-plan", "Implementation plan", "portal", "portal", f"{_SPECS}/plan.md"),
    _item("portal-research", "Research decisions", "portal", "portal", f"{_SPECS}/research.md"),
    _item("portal-data-model", "Data model", "portal", "portal", f"{_SPECS}/data-model.md"),
    _item("portal-quickstart", "Quickstart and validation", "portal", "portal",
          f"{_SPECS}/quickstart.md"),
    _item("portal-tasks", "Tasks", "portal", "portal", f"{_SPECS}/tasks.md"),
    _item("portal-checklist", "Specification quality checklist", "portal", "portal",
          f"{_SPECS}/checklists/requirements.md"),
    _item("portal-contract-http", "Contract: HTTP API", "portal", "portal",
          f"{_SPECS}/contracts/http-api.md"),
    _item("portal-contract-files", "Contract: files consumed", "portal", "portal",
          f"{_SPECS}/contracts/consumed-files.md"),
    _item("portal-contract-ui", "Contract: user interface", "portal", "portal",
          f"{_SPECS}/contracts/ui.md"),
    _item("portal-readme", "Portal README", "portal", "portal", "web-demo/README.md"),
)

# (glob relative to the repository root, group, part, id prefix, label prefix)
PATTERNS: tuple[tuple[str, str, str, str, str], ...] = (
    (f"{_B}/evidence/eval-results*.json", "historical", "1B", "1b-report", "Evaluation report"),
    (f"{_A}/evidence/harness-results/*/*", "verification", "1A", "1a-run", "Part 1A harness run"),
    (f"{_B}/evidence/unit-test-results/*.txt", "verification", "1B", "1b-unit",
     "Part 1B unit-test run"),
    (f"{_B}/evidence/eval-console/*.txt", "verification", "1B", "1b-console",
     "Part 1B evaluator console"),
    ("web-demo/evidence/harness-results/*/*", "verification", "portal", "portal-run",
     "Portal harness run"),
    ("web-demo/evidence/*.md", "verification", "portal", "portal-record", "Portal verification"),
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _eligible(path: Path, max_bytes: int) -> int | None:
    """Size in bytes if the path is an existing UTF-8 text file within the limit."""
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return None
        raw = path.read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return len(raw)


def build_index(repo_root: Path, max_bytes: int) -> list[tuple[EvidenceItem, int]]:
    entries: list[tuple[EvidenceItem, int]] = []
    for item in EXPLICIT:
        size = _eligible(repo_root / item.path, max_bytes)
        if size is not None:
            entries.append((item, size))

    for pattern, group, part, prefix, label in PATTERNS:
        for path in sorted(repo_root.glob(pattern)):
            size = _eligible(path, max_bytes)
            if size is None:
                continue
            relative = path.relative_to(repo_root).as_posix()
            folder, name = path.parent.name, path.name
            is_run_folder = re.fullmatch(r"\d{8}-\d{6}", folder) is not None
            suffix = f"{folder}-{name}" if is_run_folder else name
            detail = f"{folder} / {name}" if is_run_folder else name
            item = EvidenceItem(f"{prefix}-{_slug(suffix)}", f"{label}: {detail}", group, part,
                                relative)
            entries.append((item, size))
    return entries
