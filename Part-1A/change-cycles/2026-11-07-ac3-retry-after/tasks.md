# Tasks: AC3 Retry-After Precision and Harness Reproducibility (Part 1A, 2026-11-07)

**Plan**: [plan.md](plan.md) | Paths are relative to the repository root.

## Phase 1: Harness reproducibility

- [ ] C001 Pin `Part-1A/requirements.txt` to `fastapi==0.162.0`, `starlette==1.10.0`, `pytest==9.2.0`, `ruff==0.17.4`, `bandit==1.9.4`
- [ ] C002 Extend `Part-1A/.harness/run.ps1` so each run writes `Part-1A/evidence/harness-results/<YYYYMMDD-HHMMSS>/` with one unedited transcript per gate and `summary.json` (harness, timestamp, Python and tool versions, per-gate command/exit code/result, overall result). Gate commands, gate order and the PASS/FAIL exit-code rule MUST stay unchanged.
- [ ] C003 Update the Part 1A prerequisites in the repository `README.md` to Python 3.13 and the pinned installation
- [ ] C004 Create `Part-1A/.venv` with Python 3.13.18 from `Part-1A/requirements.txt` and run the harness on unchanged source and tests (baseline / environment verification); commit the run folder unedited

## Phase 2: Tests first (AC1, AC2, AC3)

- [ ] C005 Add to `Part-1A/tests/test_limiter.py`, without changing the existing three tests: a fake-clock fixture; `test_ac1_ac2_spec_capacity_per_tier` (Free 5, Standard 20, Premium 100 immediate requests accepted, the next one rejected with 429); `test_ac3_retry_after_is_smallest_sufficient_wait` for every tier and request spacings of 0 s, 0.01 s and 0.25 s (header is a positive integer; a retry one second before the advertised wait is rejected; a retry at exactly the advertised wait is accepted)
- [ ] C006 Run the harness; record the run folder unedited (expected: Pytest gate FAILS for AC3 on the current implementation)

## Phase 3: Repair and revalidation

- [ ] C007 Give the C006 transcript to the coding agent and repair `TokenBucket.time_until_next_token()` in `Part-1A/src/limiter.py` (no test or gate changes)
- [ ] C008 Save the repaired source as `Part-1A/evidence/final-generation/limiter_final_after_ac3_repair.py`; keep the existing snapshots unchanged; describe all snapshots in `Part-1A/evidence/README.md`
- [ ] C009 Re-run the same harness; record the run folder unedited (expected: all gates PASS)
- [ ] C010 Repository owner: write the harness-log entry for this cycle and the ACCEPT/REJECT decision (not done by the coding agent)
