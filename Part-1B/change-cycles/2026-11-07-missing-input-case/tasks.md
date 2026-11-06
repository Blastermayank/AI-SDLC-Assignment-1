# Tasks: Missing-Input Case, INV8 Revision and Report Traceability (Part 1B, 2026-11-07)

**Plan**: [plan.md](plan.md) | Paths are relative to the repository root.

## Phase 1: Environment

- [x] D001 Pin `Part-1B/requirements.txt` to `google-genai==2.33.0`, `jsonschema==4.26.0`, `pytest==9.2.0`; update the Part 1B install and evaluation instructions in `README.md` (Python 3.13; automatic archiving)
- [x] D002 Create `Part-1B/.venv` with Python 3.13.18 from `Part-1B/requirements.txt`

## Phase 2: Tests first

- [x] D003 Create `Part-1B/tests/test_evaluator.py` (loads `.harness/evaluate.py` by path; no network): INV1/INV3/INV4/INV6/INV7/INV8 behaviour of `invariant_check`, including `expected_status="error"` for `{"status": "error", "findings": []}`; SEM1-SEM3 behaviour of `semantic_check`; blank and whitespace input to `analyze_code` returns the error response without a model call; `archive_existing_report()` copies the current report byte for byte to the next `eval-results-run-<N>-<score>pct.json` and skips identical archives; `dataset_fingerprint()` returns the SHA-256 of the dataset bytes; dataset contract (unique ids, required fields, `expected_status` values, at least one `missing` case with whitespace-only input and `expected_status: error`; cases 1-15 identical to commit `2c88355`)
- [x] D004 Run `python -m pytest tests -v` and save the unedited output to `Part-1B/evidence/unit-test-results/<UTC yyyyMMdd-HHmmss>-pytest.txt` (expected: FAIL before D005-D006)

## Phase 3: Implementation

- [x] D005 Update `Part-1B/.harness/evaluate.py`: `invariant_check(output, source_code, expected_status="success")` with identical messages for existing cases; `main()` passes each case's `expected_status` and records it per result; `dataset_fingerprint()`; report adds `dataset_file` and `dataset_sha256`; `archive_existing_report()` runs before the report is written. Threshold, schema, aliases and scoring unchanged.
- [x] D006 Append case 16 to `Part-1B/evals/dataset.json`: `{"id": 16, "type": "missing", "input": "   \n\t  ", "expected_vuln": "None", "expected_status": "error"}`
- [x] D007 Re-run the unit tests; save the output as in D004 (expected: PASS)

## Phase 4: Evaluation and evidence

- [x] D008 Run `python .harness/evaluate.py` once with the live Gemini model (archives the current 86.7% report first); keep the console output in `Part-1B/evidence/eval-console/<UTC yyyyMMdd-HHmmss>.txt` — outcome: INCOMPLETE (Gemini 503 on case 15); one retry, also INCOMPLETE (503 on case 1). No further retries by the coding agent.
- [x] D009 Index all Part 1B evidence (snapshots, every saved report with its dataset consistency, unit-test runs) in `Part-1B/evidence/README.md`; update the saved-result section of `README.md` with the new current report and the archived run
- [ ] D010 Repository owner: write the harness-log entries for this cycle and the ACCEPT/REJECT decision (not done by the coding agent)
- [ ] D011 When the Gemini service is available, run the 16-case evaluation again (owner triggers or approves). The first run that completes, whether PASS or FAIL, is the result for the 16-case dataset and is recorded unedited.

Added during the cycle (2026-11-07): the dataset fingerprint was changed from file bytes to
canonical JSON content (spec Section 7 and Clarifications refined; tests first; unit-test runs
`20261106-190356` failing and `20261106-190451` passing).
