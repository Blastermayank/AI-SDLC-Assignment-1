# Change Plan: Missing-Input Evaluation Case, INV8 Revision and Report Traceability

**Part**: 1B (AI-Assisted Security Code Reviewer) | **Date**: 2026-11-07
| **Branch**: `part-1b/case-16-blank-input`

**Spec**: [../../speckit.specify.md](../../speckit.specify.md) (Clarifications, session 2026-11-07)
| **Constitution**: [../../speckit.constitution.md](../../speckit.constitution.md)

This plan covers one maintenance cycle started on 2026-11-07. It is not a reconstruction of the
original 2026-11-05/06 planning, which was not preserved.

## Trigger

- The 2026-11-06 audit found that no evaluation case covers "missing mandatory information"
  (assignment section 4.5), although spec Section 2 requires empty or whitespace-only input to
  return an error response. The repository owner chose to add the case on 2026-11-06.
- The evaluator's INV8 check treats any non-`success` status as a violation, so the correct
  behaviour for that case would be scored as a failure.
- A 2026-11-07 check of saved reports against the current dataset showed run 1 used earlier
  inputs for cases 6 and 12 and runs 2-4 an earlier input for case 6. The reports do not record
  which dataset they used.
- `evaluate.py` overwrites `evidence/eval-results.json`; preservation relied on a manual copy.
- Dependencies were unpinned.

## Scope

1. Spec revision (done): INV8 uses a per-case `expected_status`; dataset may declare it; reports
   record the dataset SHA-256; the evaluator archives the current report before writing.
2. Unit tests (new `Part-1B/tests/`, no network) for the evaluator's invariant and semantic
   checks, the reviewer's blank-input path, report archiving, and the dataset contract.
3. Evaluator changes in `Part-1B/.harness/evaluate.py`: `invariant_check(..., expected_status)`,
   dataset fingerprint in the report, archive-before-write. Threshold, aliases, schema and
   pass/fail rules unchanged.
4. Dataset: append case 16 only. Cases 1-15 unchanged.
5. Pin `google-genai==2.33.0`, `jsonschema==4.26.0`, `pytest==9.2.0`; Python 3.13.
6. One new full evaluation run (15 live Gemini calls; case 16 makes no call). The current
   86.7% report is archived first, automatically and byte for byte.

Out of scope: prompt or reviewer changes, alias changes, threshold changes, and the known
semantic failures of the saved run (cases 3 and 8).

## Constitution Check (Part 1B constitution)

| Principle | Check |
|---|---|
| Structural Reliability (well-formed JSON, exact schema) | PASS: schema unchanged; the error response for missing input already conforms |
| Deterministic Evaluation of Non-Determinism | PASS: INV8 stays a deterministic check, now driven by declared expectations |
| Fail-Safe (defined error schema, no crash) | PASS: the new case exercises exactly this behaviour |
| Evaluation Threshold (80% over the dataset) | PASS: unchanged. Note: the constitution text says "15-case dataset"; the dataset now has 16 cases. The threshold rule applies to the whole dataset; the owner may update that wording in the constitution. |

## Risks

- The new full run is non-deterministic and may score differently from 86.7% (recorded runs
  ranged from 66.7% to 93.3%). Whatever it returns is recorded unedited.
- A Gemini quota or service error stops the run as INCOMPLETE; this is reported as such, not as
  a pass or fail.
