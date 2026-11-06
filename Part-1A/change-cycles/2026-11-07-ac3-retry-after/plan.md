# Change Plan: AC3 Retry-After Precision and Harness Reproducibility

**Part**: 1A (Tiered Rate Limiter) | **Date**: 2026-11-07 | **Branch**: `part-1a/ac3-retry-after`

**Spec**: [../../speckit.specify.md](../../speckit.specify.md) (Clarifications, session 2026-11-07)
| **Constitution**: [../../speckit.constitution.md](../../speckit.constitution.md)

This plan covers one maintenance cycle that started on 2026-11-07. It is not a reconstruction of
the original 2026-11-05 plan, which was not preserved.

## Trigger

The 2026-11-06 repository audit reproduced a defect with a controlled clock: with a 10 ms gap
between Free-tier requests, the sixth request returned `Retry-After: 11`, and a retry sent
exactly 11 seconds later was rejected again. Cause: `TokenBucket.time_until_next_token()`
truncates with `int(...)`. The existing AC3 test only checks that the header exists, so the
harness could not detect this. The same audit found that the harness tools were unpinned (a
fresh install pulled pytest 9.2.0, which crashes on the machine's CPython 3.10.0), and that the
harness kept no saved results.

## Scope

1. Make AC3 testable (done in the spec's 2026-11-07 clarification).
2. Add specification-derived tests: AC3 precision across tiers and request spacings; AC1/AC2
   capacity for every tier named in the spec (5 / 20 / 100).
3. Repair `time_until_next_token()` so it returns the smallest sufficient whole number of
   seconds.
4. Make the harness reproducible: pin tool versions; run on Python 3.13; save every run's
   unedited output and a `summary.json` (format: `web-demo/specs/001-web-demo-portal/contracts/consumed-files.md`).

Out of scope: changing tiers, the token-bucket algorithm, in-memory storage, the unknown-tier
fallback, or the tier being fixed at a client's first request (all existing, documented
behaviour).

## Technical Context

- Python 3.13.18; `fastapi==0.162.0`, `starlette==1.10.0`, `pytest==9.2.0`, `ruff==0.17.4`,
  `bandit==1.9.4` (versions verified together on 2026-11-06/07).
- Tests control time by replacing the limiter module's `time` reference with a fake clock;
  production code is unchanged apart from the repair.
- The Ruff rule set is Ruff 0.17.4's default set, fixed by pinning the version. No rule is
  disabled.

## Constitution Check (Part 1A constitution)

| Principle | Check |
|---|---|
| Deterministic Behavior (strict Token Bucket) | PASS: the repair changes only the advertised wait; bucket arithmetic is unchanged |
| In-Memory Operations | PASS: no storage change |
| Security First (Bandit, zero high severity) | PASS: Bandit gate unchanged (`-ll`, medium and above) |
| Code Quality (Ruff, zero errors) | PASS: Ruff gate unchanged; version pinned |
| Python 3.10+ | PASS: 3.13.18 |
| Pytest mandatory | PASS: tests only added; none removed or weakened |

## Verification Sequence

1. Baseline harness run with the pinned tools on unchanged code (environment verification).
2. Add the new tests first and run the harness. The new AC3 tests are expected to FAIL on the
   current implementation; the run is saved as failure evidence.
3. Give the saved failure output to the coding agent; repair the implementation.
4. Re-run the same harness gates and save the run.
5. Repository owner records the harness-log entry and the ACCEPT/REJECT decision.
