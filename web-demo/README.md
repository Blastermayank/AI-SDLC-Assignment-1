# Web Demonstration Portal

A local web page that explains and demonstrates the two Assignment 1 applications:

- **Part 1A - Tiered Rate Limiter** (deterministic): send requests and watch the token bucket
  accept them or return `429 Too Many Requests` with a `Retry-After` header.
- **Part 1B - AI Security Code Reviewer** (non-deterministic): paste code and get a live
  security review from Google Gemini (`gemini-3.5-flash-lite`), checked by the same Layer 1 and
  Layer 2 rules the evaluator uses.

It also shows the saved Part 1B evaluation results and lets you browse the engineering evidence
(specifications, harness results, tests, logs).

**Scope: presentation layer only.** The portal loads `Part-1A/src/limiter.py` and
`Part-1B/.harness/evaluate.py` (which uses `Part-1B/src/reviewer.py`) exactly as they are and
never changes, re-implements or mocks them. All portal code lives in this `web-demo/` folder.

## The six sections

| Section | What you can do |
|---|---|
| Overview | What each application does, how they were built, and live status of the portal and the Gemini key |
| Methodology | The spec-driven workflow (constitution, specification, plan, tasks, harness) with links to each artifact |
| Part 1A | Pick a client ID and tier, send requests, see accepted/rejected results, remaining tokens and `Retry-After`; reset; latest saved Part 1A harness run |
| Part 1B | Load a sample or paste code, run one live Gemini review, see findings, live Layer 1/2 checks and the raw JSON |
| Evaluation | The saved Part 1B evaluation report: score, threshold, per-case layer results, and the history of every saved run. Read-only: no model is called |
| Evidence | Browse allow-listed project files read-only, with the SHA-256 of each file |

## What you need

- Windows 10 or 11 with PowerShell 5.1 or later (built in).
- Python 3.13: `winget install Python.Python.3.13` (or `uv python install 3.13`).
- Internet access the first time (to download the pinned packages).
- For live Part 1B analysis only: a Google Gemini API key stored as a Windows **user**
  environment variable named `GEMINI_API_KEY` (see below). Everything else works without it.
- Microsoft Edge (preinstalled on Windows 11) - only for the browser tests.

### Setting the Gemini key (once)

1. Press Start, type **"Edit environment variables for your account"**, and open it.
2. Under *User variables*, click **New**. Name: `GEMINI_API_KEY`. Value: your key. Click OK.
3. Open a **new** PowerShell window (old windows do not see the change).

Typing the key into this dialog keeps it out of your command history. The portal reads the key
only on the server and never shows it: pages, API responses and logs say only "configured" or
"not configured".

## Start the portal

```powershell
cd "<repository folder>\web-demo"
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

The script:

1. finds Python 3.13 and creates `web-demo\.venv` the first time;
2. installs the pinned packages from `requirements.txt` (only when that file changes);
3. prints `Gemini API key: configured (value hidden)` or `not configured`;
4. serves the portal at <http://127.0.0.1:8000> and opens your browser when it is ready.

Stop it with **Ctrl+C**. Options: `-Port 8001` to use another port, `-NoBrowser` to skip
opening the browser.

The portal listens on `127.0.0.1`, so only this computer can reach it.

## Run the portal's harness (automated checks)

```powershell
cd "<repository folder>\web-demo"
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # once (needs start.ps1 run first)
powershell -NoProfile -ExecutionPolicy Bypass -File .\.harness\run.ps1
```

Four gates run in order; the result is PASS only if all four pass:

| Gate | Command | Checks |
|---|---|---|
| SYNTAX & LINT GUARD (RUFF) | `ruff check app tests` | Code style and common bugs (rules listed in `pyproject.toml`) |
| SECURITY / SAST GUARD (BANDIT) | `bandit -r app -ll -c pyproject.toml` | Medium/high security issues in the portal code |
| API & CONTRACT TESTS (PYTEST) | `python -m pytest -m "not e2e" -v` | Every endpoint against the contracts, security headers, secret sweep, performance |
| BROWSER E2E TESTS (PLAYWRIGHT) | `python -m pytest -m e2e -v` | The real page in Microsoft Edge: interactions, 360 px layout, keyboard use, contrast |

Every run is saved, unedited, in `evidence/harness-results/<UTC date-time>/` (one transcript
per gate plus `summary.json`). The Evidence section of the portal lists these runs.

**How Gemini is handled in tests.** Automated tests never call Gemini and never see the real
key: every test removes the key and replaces only the Gemini SDK client object (the network
boundary) with a fake that returns prepared text or raises the SDK's real error types. The real
`reviewer.py` code, prompt, JSON parsing and validation still run. Live behaviour is verified
separately, by hand, and recorded in `evidence/live-gemini-verification-*.md`.

## API summary

All endpoints return JSON. The full contract, with request and response shapes, is in
[specs/001-web-demo-portal/contracts/http-api.md](specs/001-web-demo-portal/contracts/http-api.md).

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Portal status, whether Part 1A/1B loaded, whether the key is configured (never the key) |
| `GET /api/part-1a/tiers` | Tier capacities and refill rates, read from Part 1A |
| `POST /api/part-1a/request` | Send one request `{client_id, tier}` through the Part 1A limiter |
| `POST /api/part-1a/reset` | Clear the in-memory token buckets |
| `GET /api/part-1a/harness` | Latest saved Part 1A harness run |
| `POST /api/part-1b/analyze` | One live Gemini review of `{code}` (at most 20,000 characters; one at a time; 60 s limit) |
| `GET /api/part-1b/evaluation` | The saved evaluation report (`?report=<file>` for an earlier saved run) |
| `GET /api/part-1b/evaluation/history` | Summary of every saved evaluation run |
| `GET /api/evidence`, `GET /api/evidence/{id}` | Allow-listed evidence files and their contents with SHA-256 |
| `GET /api/openapi.json` | Generated OpenAPI document (`/docs` and `/redoc` are switched off) |

## Security notes

- The Gemini key stays on the server: it is read from the environment and never written to
  files, pages, responses or logs (checked by `tests/test_secret_sweep.py`).
- Submitted code is sent to Gemini for review but is **never executed**, stored or logged.
- Model output is shown as plain text (`textContent`), never as HTML. A strict
  Content-Security-Policy blocks inline scripts and `eval`.
- Evidence files are served by fixed IDs from an allow-list, so file paths cannot be requested
  (no path traversal).
- POST requests from other web sites, unexpected `Host` headers and bodies over 64 KB are
  refused. Error messages never repeat what was submitted.

## Limitations

- Part 1A's buckets live in memory: they are lost when the portal restarts (the page notices
  and clears its history).
- Live Part 1B results depend on Gemini's availability and quota, and vary between calls by
  design. The portal reports quota, service, network and timeout problems instead of hiding
  them.
- The evaluation figures shown are recorded runs, not a general accuracy guarantee.

## Troubleshooting

| Problem | What to do |
|---|---|
| `Python 3.13 was not found` | Install it (`winget install Python.Python.3.13`), open a new terminal, run `start.ps1` again |
| `running scripts is disabled on this system` | Use the full command above (`powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1`); it does not change any system setting |
| `Port 8000 is already in use` | The portal may already be running in another window; close it, or run `.\start.ps1 -Port 8001` |
| `web-demo\.venv was made with a different Python version` | Delete the `web-demo\.venv` folder and run `start.ps1` again |
| `Gemini API key: not configured` | Set `GEMINI_API_KEY` as a user variable (see above) and open a new terminal |
| Part 1B says "Gemini is not configured on the server" | The key is missing or was rejected; set or renew `GEMINI_API_KEY`, then restart the portal from a new terminal |
| Part 1B says "The Gemini service returned an error (for example, high demand)" | Gemini is temporarily overloaded (HTTP 503); wait a few minutes and try again |
| Part 1B says "The Gemini quota or rate limit was reached" | The key's quota is used up for now (HTTP 429); wait for it to reset |
| Part 1B says "Gemini did not respond within 60 seconds or could not be reached" | Check the internet connection, then try again |

## Folder layout

```text
web-demo/
  app/          FastAPI backend (loads Part 1A/1B by file path; routes; security middleware)
  static/       index.html, css/, js/ (vanilla JavaScript, no build step), img/
  tests/        API and contract tests; tests/e2e/ browser tests (Playwright + Edge)
  .harness/     run.ps1 - the portal harness
  evidence/     saved harness runs and manual verification records
  specs/001-web-demo-portal/   Spec Kit specification, plan, research, contracts, tasks
  .specify/     Spec Kit configuration and the portal constitution (.specify/memory/constitution.md)
  start.ps1     one-command start
  requirements.txt / requirements-dev.txt   pinned runtime / development packages
  portal-config.json   public GitHub repository link shown in the footer (optional)
```
