# Part 1B Evidence

This folder holds the implementation snapshots, datasets, saved evaluation reports, evaluator
console output and unit-test runs for Part 1B. Files are never edited after they are saved.
The narrative record of each cycle and the human ACCEPT/REJECT decisions are in
[`../harness-log.md`](../harness-log.md), written by the repository owner.

## Source snapshots

| File | What it is | Commit (date) |
|---|---|---|
| `initial-generation/reviewer_initial.py` | First implementation: a keyword-matching stand-in that makes no model call | `1998fc2` (2026-11-05) |
| `final-generation/reviewer_final.py` | Gemini implementation (`gemini-3.5-flash-lite`, structured JSON output, local validation); identical to `src/reviewer.py` | `2c88355` (2026-11-06) |

Commits `1998fc2` to `cf2e34b` (2026-11-05) contain the keyword-matching implementation and its
evaluator. The Gemini implementation and the current three-layer evaluator were introduced
together in `2c88355` (2026-11-06). The reviewer was not changed in the 2026-11-07 cycle.

## Datasets

| File | What it is |
|---|---|
| `../evals/dataset.json` | Current dataset: 16 cases since 2026-11-07 (case 16 added); cases 1-15 unchanged since `2c88355`. Canonical-JSON SHA-256 `f9e71665da2f8c926e06ea05a3ae8e902dc1287f541af136bd718cad4dfa1e16` |
| `dataset-before-security-refinement.json` | Intermediate dataset preserved during development (case 12 differs from the current version; case 6 matches the original) |
| `../tests/fixtures/dataset-2c88355.json` | Byte-identical copy of the 15-case dataset at `2c88355`, used by the unit tests to prove cases 1-15 are unchanged |

## Evaluation reports

`eval-results.json` is always the most recent run. Since 2026-11-07 the evaluator archives the
previous report automatically before writing a new one. Runs 1-5 were archived by hand during
development on 2026-11-06.

"Dataset check" compares every saved finding's `evidence` with today's dataset inputs (a check
run on 2026-11-07). It can only detect differences for cases where the model returned
findings. "None found" means no mismatch was detected, not a guarantee of an identical dataset.
Reports before 2026-11-07 do not record a dataset fingerprint.

| File | Timestamp (UTC) | Cases | Completed | Passed | Score | Status | Cases not passed | Dataset check | Service error | Dataset fingerprint |
|---|---|---|---|---|---|---|---|---|---|---|
| `eval-results-run-1-66.7pct.json` | 2026-11-06 05:54:57 | 15 | 15 | 10 | 66.7% | FAIL | 6, 7, 9, 12, 13 | earlier inputs for cases 6, 12 | - | not recorded |
| `eval-results-run-2-86.7pct.json` | 2026-11-06 05:57:38 | 15 | 15 | 13 | 86.7% | PASS | 4, 12 | earlier input for case 6 | - | not recorded |
| `eval-results-run-3-93.3pct.json` | 2026-11-06 05:58:51 | 15 | 15 | 14 | 93.3% | PASS | 14 | earlier input for case 6 | - | not recorded |
| `eval-results-run-4-86.7pct.json` | 2026-11-06 06:11:01 | 15 | 15 | 13 | 86.7% | PASS | 4, 12 | earlier input for case 6 | - | not recorded |
| `eval-results-run-5-86.7pct.json` | 2026-11-06 06:15:11 | 15 | 15 | 13 | 86.7% | PASS | 6, 12 | none found | - | not recorded |
| `eval-results-run-6-86.7pct.json` | 2026-11-06 06:19:02 | 15 | 15 | 13 | 86.7% | PASS | 3, 8 | none found | - | not recorded |
| `eval-results-run-7-incomplete.json` | 2026-11-06 19:02:14 | 16 | 14 | 12 | partial 85.7% (not final) | INCOMPLETE | 3, 8 (Layer 3); 15 interrupted | none found | Gemini 503 UNAVAILABLE on case 15 | `e6f3c1d2…` (file bytes, CRLF checkout) |
| `eval-results-run-8-incomplete.json` | 2026-11-06 19:02:47 | 16 | 0 | 0 | none | INCOMPLETE | 1 interrupted | - | Gemini 503 UNAVAILABLE on case 1 | `e6f3c1d2…` (file bytes, CRLF checkout) |
| `eval-results.json` | 2026-11-12 18:48:51 | 16 | 5 | 4 | partial 80.0% (not final) | INCOMPLETE | 3 (Layer 3: no finding for expected XSS); 6 interrupted | - | Gemini 503 UNAVAILABLE ("high demand") on case 6 | `f9e71665…` (canonical JSON; matches the current dataset) |

Notes:

- Run 6 was the current report at commit `2c88355` (the 86.7% result quoted in the README until
  2026-11-07). It was archived by the evaluator on 2026-11-07; its SHA-256 (`006786AB…`) is
  unchanged.
- Runs 7 and 8 and the current report were made with the revised evaluator on the 16-case
  dataset. All three were stopped by Gemini service errors ("model is currently experiencing
  high demand"), so no final score exists yet for the 16-case dataset. These are service
  failures, recorded separately from application failures as the specification requires.
  Run 8 was the current report until the evaluator archived it on 2026-11-12 (UTC); its
  content is identical to the version committed on 2026-11-07.
- Runs 7 and 8 record a file-bytes fingerprint. The fingerprint was changed to canonical JSON
  content later on 2026-11-07 because file bytes differ between CRLF and LF checkouts of the
  same dataset; the current report records the canonical value.

## Other evidence

| Folder | Contents |
|---|---|
| `eval-console/` | Unedited console output of each evaluator run since 2026-11-07 (UTC start time in the file name) |
| `unit-test-results/` | Unedited `pytest` output for `tests/test_evaluator.py`: `20261106-190039` 9 failed / 13 passed (before implementation); `20261106-190128` 22 passed; `20261106-190356` 2 failed / 21 passed (refined fingerprint requirement); `20261106-190451` 23 passed; `20261110-192616` 23 passed (cross-check on branch `001-web-demo-portal` after the portal was built, Part 1B code unchanged) |

Change-cycle plan and tasks:
[`../change-cycles/2026-11-07-missing-input-case/`](../change-cycles/2026-11-07-missing-input-case/).
