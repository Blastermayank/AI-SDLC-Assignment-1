# Contract: Files Consumed (Read-Only) by the Portal

**Feature**: `001-web-demo-portal`

The portal reads these files and never writes, renames or deletes them (Constitution II).
Paths are relative to the repository root.

| File / pattern | Owner | Used by | Format |
|---|---|---|---|
| `Part-1A/src/limiter.py` | Part 1A | Imported as `part1a_limiter` | Python module exposing `TIERS`, `TokenBucket`, `RateLimiter` |
| `Part-1B/.harness/evaluate.py` | Part 1B | Imported as `part1b_evaluate` | Python module exposing `analyze_code`, `MODEL`, `RESPONSE_SCHEMA`, `invariant_check`, `validate` |
| `Part-1B/src/reviewer.py` | Part 1B | Imported indirectly by `evaluate.py` | Python module |
| `Part-1B/evidence/eval-results.json` | Part 1B harness | Current evaluation report | Report JSON written by `evaluate.py` (fields in data model) |
| `Part-1B/evidence/eval-results-run-*.json` | Part 1B (preserved history) | Run history | Same report JSON |
| `Part-1B/evals/dataset.json` | Part 1B | Case inputs for the current report | JSON array of `{id, type, input, expected_vuln}`; may start with a UTF-8 BOM |
| `Part-1A/evidence/harness-results/<YYYYMMDD-HHMMSS>/summary.json` | Part 1A harness (to be added in Part 1A's own SDD cycle) | Part 1A harness panel | Harness run summary, below |
| `web-demo/evidence/harness-results/<YYYYMMDD-HHMMSS>/summary.json` | web-demo harness | Evidence section | Harness run summary, below |
| Allow-listed specs, sources, tests, logs and snapshots | Part 1A / Part 1B / portal | Evidence section | UTF-8 text |

## Harness run summary format (shared by Part 1A and web-demo harnesses)

One directory per run, named with the UTC start time `YYYYMMDD-HHMMSS`:

```text
<project>/evidence/harness-results/20261107-101500/
├── summary.json
├── 01-ruff.txt
├── 02-bandit.txt
└── 03-pytest.txt
```

`summary.json`:

```json
{
  "harness": "Part-1A",
  "timestamp_utc": "2026-11-07T10:15:00Z",
  "python": "3.13.18",
  "tools": { "ruff": "0.17.4", "bandit": "1.9.4", "pytest": "9.2.0" },
  "gates": [
    { "name": "SYNTAX & LINT GUARD (RUFF)", "command": "ruff check src/", "exit_code": 0,
      "result": "PASS", "transcript": "01-ruff.txt" }
  ],
  "result": "PASS"
}
```

Rules: `result` is `PASS` only if every gate's `exit_code` is 0. Transcripts contain the
gate's combined stdout/stderr, unedited. The latest run is the lexicographically greatest
directory name containing a valid `summary.json`. The portal reads only files named in
`summary.json` and located inside that run directory.
