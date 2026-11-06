# Implementation Plan: Assignment 1 Web Demonstration Portal

**Branch**: `001-web-demo-portal` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `web-demo/specs/001-web-demo-portal/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A local web portal that explains Assignment 1 and demonstrates both assessed applications
through their real code. A FastAPI backend in `web-demo/` loads `Part-1A/src/limiter.py` and
`Part-1B/.harness/evaluate.py` (which loads `Part-1B/src/reviewer.py`) by file path, and exposes
a small JSON API:
- real HTTP 429 and `Retry-After` from the Part 1A limiter
- live Gemini analyses from the Part 1B reviewer, with the harness's Layer 1/2 checks applied
- read-only views of saved evaluation reports, run history, harness results and allow-listed
  evidence files

A static HTML/CSS/vanilla-JavaScript frontend with no build step renders everything as text
under a strict Content-Security-Policy. Verification uses pytest with FastAPI `TestClient`
against the real limiter and real reviewer code (Gemini replaced only at the SDK client
boundary), Playwright browser tests on the installed Edge, Ruff and Bandit. Everything runs
from a single PowerShell harness that saves its results as evidence. See
[research.md](research.md) for the probed decisions.

## Technical Context

**Language/Version**: Python 3.13.18 (backend, tests); HTML5, CSS, ECMAScript 2022 modules (frontend)

**Primary Dependencies**: FastAPI 0.162.0, Starlette 1.10.0, Uvicorn 0.54.0, Pydantic 2.14.3,
google-genai 2.33.0 (used by Part 1B's reviewer), jsonschema 4.26.0 (used by Part 1B's
harness), httpx 0.28.1. Dev/harness: pytest 9.2.0, httpx2 2.16.0, Ruff 0.17.4, Bandit 1.9.4,
Playwright 1.64.1.

**Storage**: None owned. Read-only files from Part 1A/1B (see
[contracts/consumed-files.md](contracts/consumed-files.md)); rate-limit state in process memory;
request history in browser memory.

**Testing**: pytest + FastAPI `TestClient` (API, security, evidence, static-safety tests);
Playwright with `channel="msedge"` (browser tests); recorded manual live-Gemini check.

**Target Platform**: Windows 10/11 desktop, served on `127.0.0.1`; current Chrome/Edge.

**Project Type**: Web application (single backend serving a static frontend).

**Performance Goals**: First page render < 1 s locally; non-Gemini API responses < 200 ms;
Gemini analyses bounded at 60 s.

**Constraints**: Offline except the Gemini call; no CDN; CSP without `unsafe-inline`; request
bodies ≤ 64 KB; code ≤ 20,000 characters; one analysis in flight; no writes under `Part-1A/` or
`Part-1B/`.

**Scale/Scope**: One local user; six page sections; 10 API endpoints; about 15 Python modules
and 8 JavaScript modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Pre-research | Post-design |
|---|---|---|---|
| I. Wrap, Never Rewrite | Limiter, reviewer, schema, invariants come from Part 1A/1B modules; no copies; no writes under Part-1A/1B | PASS | PASS: R3 importlib loading with bytecode writes disabled; R4 reuses `HTTPException` status/headers; R7 reuses `RESPONSE_SCHEMA`/`invariant_check` |
| II. Evidence Integrity | Reports/evidence read-only; `evaluate.py` main never run; failures shown; accurate claims | PASS | PASS: contracts mark all evaluation/evidence endpoints read-only; R13 avoids mis-joining old runs; history caveat in API contract |
| III. Secret Confinement | Key backend-only; boolean status | PASS | PASS: `/api/health` returns `configured` boolean; fixed error messages (R5); sentinel-key leak test planned (SC-005) |
| IV. Untrusted Input and Output | No execution of code; validation; text-only rendering; CSP; no stack traces | PASS | PASS: R9 controls (CSP, custom 422 handler without echo, body limit, host/origin checks); R10 no-HTML-sink rule enforced by test |
| V. Real Behaviour, Honest Failures | Real 429; live Gemini; distinct failure categories | PASS | PASS: R5 classification table with 8 distinct categories; no simulated outcomes in JS (UI contract) |
| VI. Local-First Simplicity | FastAPI + static frontend; 127.0.0.1; one start command; pinned deps; no CDN | PASS | PASS: R14 `start.ps1`; R1 pins; Swagger/ReDoc disabled (R9). New dependencies justified: `httpx2` (Starlette 1.10 test client), `playwright` (browser verification of SC-007/SC-009, uses installed Edge) |
| VII. Specification-Derived Verification | Every FR mapped to a test or recorded manual check; harness gates; no weakening | PASS | PASS: R11 strategy; R12 harness with saved evidence; manual live-Gemini record in quickstart |

**Result**: All gates pass. No violations; Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
web-demo/specs/001-web-demo-portal/
├── spec.md              # /speckit-specify + /speckit-clarify output
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── http-api.md
│   ├── consumed-files.md
│   └── ui.md
├── checklists/
│   └── requirements.md  # /speckit-specify quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
Assignment-1/                     # repository root
├── Part-1A/                      # unchanged by this feature (read-only dependency)
├── Part-1B/                      # unchanged by this feature (read-only dependency)
└── web-demo/
    ├── .specify/ .claude/        # Spec Kit (portal only)
    ├── specs/001-web-demo-portal/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py               # app factory: middleware, routers, static mount, error handlers
    │   ├── config.py             # repository paths, limits, allowed hosts (overridable in tests)
    │   ├── backends.py           # importlib loading of part1a_limiter and part1b_evaluate
    │   ├── security.py           # security headers, body limit, origin check, request logging
    │   ├── errors.py             # ErrorEnvelope, categories, exception handlers
    │   ├── schemas.py            # Pydantic request/response models
    │   ├── harness_results.py    # read latest harness summary.json + transcripts
    │   ├── evidence_index.py     # evidence allow-list
    │   └── routes/
    │       ├── health.py
    │       ├── part1a.py
    │       ├── part1b.py
    │       ├── evaluation.py
    │       └── evidence.py
    ├── portal-config.json        # repository_url (FR-004), edited by the owner
    ├── static/
    │   ├── index.html            # six sections, static explanatory content
    │   ├── css/portal.css
    │   ├── img/icon.svg          # page icon (avoids favicon 404, research R16)
    │   └── js/
    │       ├── app.js            # router, theme, health badge, repository link
    │       ├── api.js            # fetch wrapper, error envelope handling
    │       ├── dom.js            # safe element builders (textContent only)
    │       ├── part1a.js
    │       ├── part1b.js
    │       ├── evaluation.js
    │       ├── methodology.js    # artifact availability chips
    │       └── evidence.js
    ├── tests/
    │   ├── conftest.py           # app fixture, sentinel key, fake Gemini client, tmp report dirs
    │   ├── fixtures/             # copies of reference reports for deterministic tests
    │   ├── test_backends.py
    │   ├── test_health.py
    │   ├── test_security.py
    │   ├── test_part1a_api.py
    │   ├── test_harness_results.py
    │   ├── test_part1b_api.py
    │   ├── test_evaluation_api.py
    │   ├── test_evidence_api.py
    │   ├── test_static_content.py
    │   ├── test_static_safety.py
    │   ├── test_secret_sweep.py
    │   ├── test_performance.py
    │   └── e2e/                  # Playwright + installed Edge (research R11, R16)
    │       ├── conftest.py
    │       ├── test_part1a_ui.py
    │       ├── test_part1b_ui.py
    │       ├── test_evaluation_ui.py
    │       ├── test_overview_ui.py
    │       ├── test_evidence_ui.py
    │       └── test_responsive_a11y.py
    ├── .harness/
    │   └── run.ps1               # Ruff, Bandit, Pytest API, Pytest E2E; saves evidence
    ├── evidence/
    │   └── harness-results/      # harness output per run (committed as evidence)
    ├── pyproject.toml            # Ruff (explicit rule selection), pytest, Bandit configuration
    ├── requirements.txt          # runtime pins
    ├── requirements-dev.txt      # test and harness pins (includes requirements.txt)
    ├── start.ps1                 # one-command start on Windows
    └── README.md                 # portal-specific run notes
```

**Structure Decision**: A single web project under `web-demo/` with an `app/` backend package
and a `static/` frontend served by the same process (no separate frontend project because there
is no build step). Part 1A and Part 1B stay where they are and are consumed read-only, so
their imports, harnesses and evidence paths are unaffected. This replaces the handover's
suggested `web-demo/app.py` + `templates/` layout: a package keeps routes, security and loading
separately testable, and templates are unnecessary because all dynamic data comes from the JSON
API.

## Dependencies on Other Work (outside this feature)

- **Part 1A harness results** (FR-017): Part 1A's `run.ps1` must save runs in the
  [consumed-files](contracts/consumed-files.md) format. This is a Part 1A change, made in Part
  1A's own SDD cycle together with the `Retry-After` fix. Until then the panel shows "No saved
  harness results".
- **Part 1B dependency pins**: Part 1B's `requirements.txt` should pin `google-genai==2.33.0`
  and `jsonschema==4.26.0` (research R2) in Part 1B's own cycle.
- **Part 1B case 16**: will produce a new current report; the dashboard is data-driven (FR-030)
  and needs no change.

## Complexity Tracking

No constitution violations; table intentionally empty.
