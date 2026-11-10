# Quickstart validation record - 2026-11-10

Task T060 (SC-008 fresh-start timing; quickstart scenarios V1-V13). Recorded automatically by
scratch driver scripts run by the coding agent; observations are unedited. This is an
automated walk-through in Microsoft Edge (Playwright), not a hand walk-through by the owner.

- Portal commit: `b620052`
- Walk-through finished: 2026-11-10T18:49:56Z
- Scenarios passed: 12 of 13

## Fresh-start timing (SC-008, target 10 minutes or less)

Method: `web-demo\.venv` deleted; pip's download cache disabled (`PIP_NO_CACHE_DIR=1`) so every
package was downloaded; `start.ps1` run exactly as documented (browser opening included).
Times are measured from launch (second precision), using the timestamps in the portal's own
request log. The timing script's live polling of that log failed (Windows kept the file locked
while the server ran), so the times were computed from the log after the server stopped.
The browser tab that opened was then used by hand for a few minutes; those later requests
are not part of the timing.

- Launched (local time): 2026-11-11 00:04:03
- Portal answering `/api/health` (virtual environment created, packages installed): 94.7 s
- Default browser requested the page: 96.6 s
- Page scripts ran and called `/api/health` (overview visible): 96.7 s
- SC-008: met

`start.ps1` output on the fresh start:

```text
[portal] Creating the virtual environment with 'python3.13' (first run only)...
[portal] Using Python 3.13.18 (E:\Mtech Assignment\AI_SDLC\Assignment-1\web-demo\.venv\Scripts\python.exe)
[portal] Installing pinned packages from requirements.txt (this can take a few minutes)...
[portal] Gemini API key: configured (value hidden)
[portal] Portal: http://127.0.0.1:8000/  (only this computer can reach it; press Ctrl+C to stop)
```

## Scenarios

Run against the portal started with `start.ps1 -Port 8002 -NoBrowser`; V8 used a second
instance started directly with uvicorn on port 8001 in an environment without
`GEMINI_API_KEY`, because `start.ps1` deliberately loads the saved user key.

| # | Story | Steps | Expected | Result |
|---|---|---|---|---|
| V1 | US1 | Part 1A: client `video-demo`, tier Free, Send 6 times | Rows 1-5 ACCEPTED/200; row 6 REJECTED/429 with `Retry-After` >= 1 s | PASS |
| V2 | US1 | Then send as client `other-client` | ACCEPTED/200 (isolation) | PASS |
| V3 | US1 | Send as `video-demo` with tier Premium | Warning: registered on Free; capacity 5 shown | PASS |
| V4 | US1 | Press Reset, then send as `video-demo` | History cleared; request ACCEPTED | PASS |
| V5 | US1 | Client ID `bad id!` | Validation message; no history row added | PASS |
| V6 | US2 | Part 1B: load the SQL sample, Analyze (one live Gemini call) | Loading state, then findings with all five fields, model name, elapsed time, Layer 1/2 results, Layer 3 "not applicable", raw JSON | FAIL |
| V7 | US2 | Submit only spaces | Analyze button disabled; API returns 422 if called directly | PASS |
| V8 | US2 | Portal started without `GEMINI_API_KEY` (second instance), Analyze | "Gemini not configured" message; no findings | PASS |
| V9 | US3 | Evaluation: open dashboard (current report, then run 6) | Figures identical to `Part-1B/evidence/eval-results.json`; failed cases flagged with explanation; history table with caveat | PASS |
| V10 | US4 | Overview and Methodology; Part 1A harness panel | Both applications, Gemini model, workflow stages, limitations; Part 1A harness panel shows latest saved run | PASS |
| V11 | US5 | Evidence: open `Part-1B/evals/dataset.json` | Content and SHA-256 match the file | PASS |
| V12 | Security | `Invoke-WebRequest http://127.0.0.1:<port>/api/evidence/..%2F..%2FREADME.md` | 404 `not_found` | PASS |
| V13 | Security | Inspect page source and every network response of this walkthrough | No API key anywhere; `Content-Security-Policy` header present | PASS |

## Observed

- **V1** (PASS): Rows (oldest first): 12:19:41 am video-demo free ACCEPTED 200 - 4.00 / 12:19:41 am video-demo free ACCEPTED 200 - 3.00 / 12:19:41 am video-demo free ACCEPTED 200 - 2.01 / 12:19:41 am video-demo free ACCEPTED 200 - 1.01 / 12:19:41 am video-demo free ACCEPTED 200 - 0.02 / 12:19:41 am video-demo free REJECTED 429 12 s 0.02. Last outcome: REJECTED HTTP 429 Too Many Requests Retry-After: 12 s (from the server's response header) Client "video-demo" · free bucket · 0.02 of 5 tokens left
- **V2** (PASS): Newest row: 12:19:41 am other-client free ACCEPTED 200 - 4.00
- **V3** (PASS): Warning: Client "video-demo" is registered on the free tier (capacity 5) from its first request. Part 1A keeps that tier, so this request used the free bucket, not premium.
- **V4** (PASS): After Reset: 0 rows, notice "Demonstration reset: 2 client bucket(s) cleared. Tier settings are unchanged.". Then: 12:19:41 am video-demo free ACCEPTED 200 - 4.00
- **V5** (PASS): Message: Invalid input HTTP 422 The request contains invalid input. Check: client_id.. History rows before/after: 1/1
- **V6** (FAIL): Loading state seen: True. Outcome: service error The Gemini service returned an error (for example, high demand). No analysis was made; try again later. (HTTP 502); no retry made
- **V7** (PASS): Analyze disabled: True. Direct API call: HTTP 422, category `invalid_input`
- **V8** (PASS): Health badge: "Portal OK · Gemini not configured". Status: "not configured Gemini is not configured on the server (GEMINI_API_KEY missing or rejected). No analysis was made.". Finding cards: 0
- **V9** (PASS): Current report summary: Status INCOMPLETE Score none Threshold 80% Completed 0 / 16 Passed 0 Model gemini-3.5-flash-lite. File: status INCOMPLETE, model gemini-3.5-flash-lite, 0 / 16 completed, 1 result rows; page case rows 1. History rows 8 for 8 saved report files; caveat shown: True. Run 6 view: failed cases ['3', '8'], Layer 3 explanation shown: True
- **V10** (PASS): Missing statements: none. Part 1A harness panel: Run (UTC) 2026-11-06 18:56:25 UTC Python 3.13.18 Tools ruff 0.17.4, bandit 1.9.4, pytest 9.2.0 Gate Command Exit code Result SYNTAX & LINT GUARD (RUFF) ruff check src/ 0 PASS SECURITY / SAST GUARD (BANDIT) bandit -r src/ -ll 0 PASS UNIT ... (latest saved run folder 20261106-185625, result PASS)
- **V11** (PASS): Viewer path shown; SHA-256 on page matches file (e6f3c1d2fc60c0c2...): True; content identical to the file (line endings normalised): True
- **V12** (PASS): `Invoke-WebRequest` (PowerShell) result: HTTP 404, category `not_found`
- **V13** (PASS): 41 network responses captured during V1-V12, 41 bodies searched (0 not retrievable), plus page source and DOM: key found 0 times. Content-Security-Policy on the page response: True
