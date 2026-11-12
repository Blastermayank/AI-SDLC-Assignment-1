# Part 1B Harness Log

## Evaluation Configuration
- **Model/Configuration**: Mocked AI (Python deterministic proxy for testing evaluation layers).
- **Threshold**: 80.0% aggregate pass rate across 15 cases.

## Harness Execution 1: Failure
- **Results**: Aggregate Score 86.7% (13/15 passed).
- **Failures Captured**:
  - Case 1 FAILED: INV1 Failed: Invalid severity level. (Agent returned 'Critical' instead of High/Medium/Low).
  - Case 9 FAILED: Layer 1 Failed: Output is not valid JSON. (Agent returned a plain text string).

## Harness-Driven Repair
- **Evidence Supplied**: The JSON structural failure and the property validation failure from the terminal output.
- **Repair**: 
  1. Updated the prompt/logic to strictly map "Critical" vulnerabilities to "High" to satisfy INV1.
  2. Enforced a JSON error schema { "status": "error", "findings": [] } for malformed inputs rather than returning plain text strings.

## Harness Execution 2: Success
- **Results**: Aggregate Score 100.0%. All structural, invariant, and semantic checks passed.

## Human Review
- **Decision**: ACCEPT.
- **Limitations**: The AI reviewer currently relies on a strict keyword-based mapping (mocked). In a production setting using an LLM, the semantic evaluation layer (Layer 3) would require an independent LLM-as-a-Judge rather than string comparison, and prompt injection risks require stronger upstream filtering.

---

## Final Version: Gemini (recorded 2026-11-13)

The entries above were recorded on 2026-11-05 for the first version. The entries below cover the final version, which calls Gemini (commit `2c88355`, 2026-11-06).

- **Model/Configuration**: gemini-3.5-flash-lite
- **Result**: Incomplete due to Gemini being busy.
- **Evidence**:
  - Latest completed run: run 6, 86.7% (13/15 cases), PASS against the 80% threshold (`evidence/eval-results-run-6-86.7pct.json`).
  - 16-case dataset: runs 7-17 and the current `evidence/eval-results.json` are all INCOMPLETE (Gemini 503 "high demand"); furthest attempt: 13 of 16 cases completed, 11 passed.
  - Every run is listed in `evidence/README.md`.

## Human Review (2026-11-13)
- **Decision**: ACCEPT.
- **Reason**: Gemini was busy, so it was not performing all the scans, which left the scan incomplete and finally failed. If Gemini gets stable, the scan can complete almost every time, and based on the scan we can finally answer whether we should accept it or reject it.
- **Limitations**: Gemini is unstable, which causes denial of service when we need it.
