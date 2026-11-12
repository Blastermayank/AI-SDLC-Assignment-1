# Testing, Harnesses and Evidence

How each part is verified, where the saved proof lives, and how to check it yourself.
Evidence files are saved by scripts and never edited afterwards; failures are kept alongside
passes.

## 1. Overview

| What is checked | How | Command (from the folder shown) | Saved evidence |
|---|---|---|---|
| Part 1A code quality, security and behaviour | Harness: Ruff, Bandit, Pytest | `Part-1A>` `powershell -NoProfile -ExecutionPolicy Bypass -File .\.harness\run.ps1` | `Part-1A/evidence/harness-results/<run>/` |
| Part 1B evaluator logic (offline) | Pytest unit tests, no network, no key | `Part-1B>` `.\.venv\Scripts\python.exe -m pytest tests -v` | `Part-1B/evidence/unit-test-results/` |
| Part 1B model behaviour (live Gemini) | Three-layer evaluation over `evals/dataset.json` | `Part-1B>` `.\.venv\Scripts\python.exe .\.harness\evaluate.py` | `Part-1B/evidence/eval-results*.json`, `eval-console/` |
| Web portal | Harness: Ruff, Bandit, Pytest API tests, Pytest browser tests (Edge) | `web-demo>` `powershell -NoProfile -ExecutionPolicy Bypass -File .\.harness\run.ps1` | `web-demo/evidence/harness-results/<run>/` |
| Portal with live Gemini, and a fresh start | Recorded walk-throughs | see `web-demo/specs/001-web-demo-portal/quickstart.md` | `web-demo/evidence/*.md` |

Harness run folders are named by UTC start time (`yyyyMMdd-HHmmss`) and contain one
transcript per gate plus `summary.json` (Python and tool versions; each gate's command, exit
code and result). A harness result is PASS only if every gate exits with code 0.

## 2. Part 1A

Gates (`Part-1A/.harness/run.ps1`):

1. `ruff check src/`: lint and import order.
2. `bandit -r src/ -ll`: static security analysis (medium and high severity).
3. `python -m pytest tests/ -v`: tests derived from the acceptance criteria. AC1/AC2 capacity
   per tier, AC2 HTTP 429, AC3 `Retry-After` equal to the smallest sufficient whole-second wait
   (checked with a fake clock: waiting exactly that long succeeds, one second less fails),
   AC4 per-client isolation.

Saved runs (full table: [Part-1A/evidence/README.md](../Part-1A/evidence/README.md)):

| Run (UTC) | Context | Result |
|---|---|---|
| `20261106-185500` | Baseline before the AC3 change cycle (3 tests) | PASS |
| `20261106-185552` | New spec-derived tests added, implementation unchanged | **FAIL** (3 of 15 tests) |
| `20261106-185625` | After the AC3 repair | PASS (15/15) |
| `20261110-192610` | Cross-check after the web portal was built | PASS (15/15) |

Earlier history (the first generation and its first failure-and-repair cycle) is in
`Part-1A/evidence/initial-generation/`, `final-generation/` and `Part-1A/harness-log.md`.

## 3. Part 1B

### Unit tests (offline)

`Part-1B/tests/test_evaluator.py`: 23 tests of the evaluator itself: Layer 2 invariants
(including per-case `expected_status`), case 16 handling without a model call, the dataset
fingerprint, and archiving. A fixture copy of the original 15-case dataset checks that the
original cases are unchanged. Saved runs show the tests failing before the implementation and
passing after (see [Part-1B/evidence/README.md](../Part-1B/evidence/README.md)).

### Live evaluation

The pipeline, layers and scoring are described in [architecture.md](architecture.md#evaluation-harness-part-1bharnessevaluatepy).
Threshold **80%**, declared in `Part-1B/speckit.specify.md` before evaluation. Exit codes:
0 PASS, 1 FAIL, 2 INCOMPLETE.

Saved reports (every run is kept; the full table, including which runs used earlier dataset
inputs, is in [Part-1B/evidence/README.md](../Part-1B/evidence/README.md)):

| Report | Cases | Result |
|---|---|---|
| Runs 1-6 (2026-11-06) | 15 | 66.7% FAIL, then 86.7%, 93.3%, 86.7%, 86.7%, 86.7% (all PASS). Runs 1-4 used earlier inputs for some cases |
| Run 6, latest completed | 15 | 86.7% PASS; cases 3 and 8 failed Layer 3 |
| Run 7 | 16 | INCOMPLETE: Gemini 503 on case 15 (14 completed, 12 passed; partial, not final) |
| Run 8 | 16 | INCOMPLETE: Gemini 503 on case 1 |
| Runs 9-17 (2026-11-13 local) | 16 | INCOMPLETE: Gemini 503 (one dropped connection) after 0-5 completed cases |
| Current `eval-results.json` (2026-11-13 local) | 16 | INCOMPLETE: Gemini 503 on case 14 (13 completed, 11 passed; cases 3 and 8 failed Layer 3; partial 84.6%, not final) |

The 16-case dataset has no completed run yet. Service errors stop a
run as INCOMPLETE and are never counted as application failures or passes.

## 4. Web portal

Gates (`web-demo/.harness/run.ps1`): `ruff check app tests`;
`bandit -r app -ll -c pyproject.toml`; `python -m pytest -m "not e2e" -v` (API, contract,
security, secret-sweep, static-safety and performance tests); `python -m pytest -m e2e -v`
(browser tests in Microsoft Edge via Playwright: every section, keyboard use, 360 px layout,
WCAG AA contrast, console errors).

**How Gemini is handled in portal tests:** every test removes the API key and replaces only
the Gemini SDK client object with a fake that returns prepared text or raises the SDK's real
error classes. The real `reviewer.py` prompt, parsing and validation, and the evaluator's
Layer 1 and Layer 2 checks, still run. Live behaviour is verified separately (below).

| Evidence | Result |
|---|---|
| `harness-results/20261110-182635` | PASS: 171 API and 36 browser tests |
| `harness-results/20261110-185030` | PASS: 177 API and 36 browser tests (final state) |
| `live-gemini-verification-20261110.md` | 10 live submissions through the page: 9 displayed results, 1 Gemini service error, all within 60 s |
| `quickstart-validation-20261110.md` | Fresh start (new environment, packages downloaded) to visible page in 96.7 s; scenarios V1-V13: 12 PASS, V6 FAIL due to a Gemini service error (not retried) |

## 5. Change cycles (specification → tests → failure → repair → pass)

Both parts went through a recorded change cycle on 2026-11-07. Each started with a
clarification in the specification, followed by a plan and tasks, then tests written before
the code, a recorded failure, the repair, and a recorded pass.

**Part 1A: AC3 `Retry-After` precision** (`Part-1A/change-cycles/2026-11-07-ac3-retry-after/`)

| Commit | Step |
|---|---|
| `e9d39a4` | Clarify AC3 in `speckit.specify.md` |
| `5bde213` | Plan and tasks |
| `0988cde` | Pin tools; harness saves every run |
| `11b6a4b` | Baseline harness run (PASS) |
| `c40d7d4` | Spec-derived AC1/AC2/AC3 tests |
| `8d71a7e` | Harness run FAILS on clarified AC3 |
| `ca00520` | Repair: round `Retry-After` up to the smallest sufficient wait |
| `2da2945` | Harness PASS; final snapshot and evidence index |

**Part 1B: missing-input case and expected status**
(`Part-1B/change-cycles/2026-11-07-missing-input-case/`)

| Commit | Step |
|---|---|
| `3ca2ef3` | Clarify the missing-input case and revise INV8 in `speckit.specify.md` |
| `fddcb59` | Plan and tasks |
| `3616aa5` | Pin dependencies; Python 3.13 |
| `e035cbd`, `762b517` | Spec-derived unit tests; they FAIL before implementation |
| `aa33e24`, `603b83c` | Per-case expected status, fingerprint, archiving; case 16 |
| `4c9c594` | Unit tests PASS |
| `0c07435`, `064d08b` | Live evaluation INCOMPLETE twice (Gemini 503) |
| `0ccc73b`, `b7e0f97` | Fingerprint must ignore line endings: test FAIL, then fix and PASS |
| `6c611b8` | Evidence index and README status |

## 6. Verify the evidence yourself

- **File identity:** `Get-FileHash -Algorithm SHA256 <file>`. The portal's Evidence section
  shows the same SHA-256 for each file it lists.
- **Dataset fingerprint** recorded in reports from the revised evaluator (canonical JSON, so it
  is identical on CRLF and LF checkouts). From `Part-1B`:

  ```powershell
  @'
  import sys
  sys.path.insert(0, ".harness")
  import evaluate
  print(evaluate.dataset_fingerprint(evaluate.DATASET_FILE))
  '@ | .\.venv\Scripts\python.exe -
  ```

  The two INCOMPLETE reports of 2026-11-07 predate this method and record a file-bytes hash
  instead (explained in `Part-1B/evidence/README.md`).
- **History:** `git log --oneline -- Part-1A` and `git log --oneline -- Part-1B` list every
  change in order. Evidence commits contain the saved files unchanged.

## 7. Fresh-clone check of the instructions (2026-11-11)

To confirm the README instructions work as written, the repository (commit `3f0254b`) was
cloned into an empty folder and the documented steps were followed in Windows PowerShell 5.1
with Python 3.13.18:

| Part | Steps followed | Outcome |
|---|---|---|
| Part 1A | README "Installation", then "Run the Part 1A harness" and the separate test command | Harness PASS (Ruff, Bandit, Pytest); 15 tests passed |
| Part 1B | README "Installation", key check, "Run a sample analysis" (one live Gemini call), unit tests, the fingerprint command above | Sample returned a schema-valid SQL Injection finding; 23 tests passed; fingerprint `f9e71665…` |
| Web portal | `start.ps1` (created its own virtual environment), then `requirements-dev.txt` and the portal harness | Portal answered on `/api/health`; harness PASS (177 API, 36 browser tests) |

The full Part 1B evaluation was not run in this check: it makes 16 live calls, and its next
run is reserved as the recorded result for the 16-case dataset.

## 8. Rules followed

From the assignment and the projects' constitutions: no difficult test or dataset case was
removed; the 80% threshold was not changed; no validation layer was disabled; specification
changes went through recorded clarifications; failing runs were kept; Gemini service errors
are reported as INCOMPLETE rather than hidden or counted as passes; the API key is read only
from the environment and never committed.
