# Quickstart and Validation Guide: Web Demonstration Portal

**Feature**: `001-web-demo-portal`

This guide proves the feature works end to end. It references the contracts rather than
repeating them.

## Prerequisites

- Windows 10/11 with PowerShell 5.1 or later.
- Python 3.13 (`winget install Python.Python.3.13`, or `uv python install 3.13`).
- Microsoft Edge (preinstalled on Windows 11; used only by the browser tests).
- For Part 1B live analysis: network access and `GEMINI_API_KEY` set as a Windows user
  environment variable (open a new terminal after setting it). The key is never displayed.

## Start the portal

```powershell
Set-Location "<repository>\web-demo"
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

Expected: the script reports the Python version, installs pinned packages on first run, prints
`Gemini API key: configured (value hidden)` or `not configured`, and serves
`http://127.0.0.1:8000`. Stop with Ctrl+C.

## Run the portal harness

```powershell
Set-Location "<repository>\web-demo"
powershell -NoProfile -ExecutionPolicy Bypass -File .\.harness\run.ps1
```

Expected: four gates (Ruff, Bandit, Pytest API, Pytest browser) each report PASS, the summary
prints `HARNESS RESULT: PASS`, exit code 0, and a new folder appears under
`evidence/harness-results/` containing `summary.json` and one transcript per gate
([contracts/consumed-files.md](contracts/consumed-files.md)).

## Validation scenarios

| # | Story | Steps | Expected outcome |
|---|---|---|---|
| V1 | US1 | Part 1A: client `video-demo`, tier Free, press Send 6 times quickly | Rows 1-5 ACCEPTED/200; row 6 REJECTED/429 with `Retry-After` ≥ 1 s |
| V2 | US1 | Same, then send as client `other-client` | ACCEPTED/200 (isolation) |
| V3 | US1 | Send as `video-demo` with tier Premium | Warning: registered on Free; capacity 5 shown |
| V4 | US1 | Press Reset, then send as `video-demo` | History cleared; request ACCEPTED |
| V5 | US1 | Client ID `bad id!` | Validation message; no history row added |
| V6 | US2 | Part 1B: load the SQL sample, Analyze | Loading state, then findings with all five fields, model name, elapsed time, Layer 1/2 results, Layer 3 "not applicable", raw JSON |
| V7 | US2 | Submit only spaces | Analyze button disabled; API returns 422 if called directly |
| V8 | US2 | Start the portal without `GEMINI_API_KEY`, Analyze | "Gemini not configured" message; no findings |
| V9 | US3 | Evaluation: open dashboard | Figures identical to `Part-1B/evidence/eval-results.json`; failed cases flagged with explanation; history table with caveat |
| V10 | US4 | Overview and Methodology | Both applications, Gemini model, workflow stages, limitations; Part 1A harness panel shows latest saved run or "No saved harness results" |
| V11 | US5 | Evidence: open `Part-1B/evals/dataset.json` | Content and SHA-256 match the file (`Get-FileHash -Algorithm SHA256`) |
| V12 | Security | `Invoke-WebRequest http://127.0.0.1:8000/api/evidence/..%2F..%2FREADME.md` | 404 `not_found` |
| V13 | Security | View page source and Network responses | No API key anywhere; `Content-Security-Policy` header present |

V6 makes one live Gemini call. Record its date, model and outcome in the verification evidence;
results vary between calls by design.

## Live Gemini verification record (manual, FR-020 / SC-004)

Run V6 with three different samples (SQL injection, command injection, a benign function).
Record for each: timestamp, model, elapsed time, number of findings, live Layer 1/2 result.
Save the record under `web-demo/evidence/` as part of the verification evidence.
