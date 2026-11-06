# Phase 0 Research: Assignment 1 Web Demonstration Portal

**Feature**: `001-web-demo-portal` | **Date**: 2026-11-07 | **Plan**: [plan.md](plan.md)

Every decision below was checked with a local probe on 2026-11-06/07 (Windows 11, uv 0.13.7,
CPython 3.13.18) unless marked otherwise. Probe scripts were run from a scratch directory outside
the repository; no repository file was modified by them.

## R1. Runtime and pinned dependencies

- **Decision**: CPython 3.13.18. Runtime pins: `fastapi==0.162.0`, `starlette==1.10.0`,
  `uvicorn==0.54.0`, `pydantic==2.14.3`, `google-genai==2.33.0`, `httpx==0.28.1`,
  `jsonschema==4.26.0`. Development/harness pins: `pytest==9.2.0`, `httpx2==2.16.0`,
  `ruff==0.17.4`, `bandit==1.9.4`, `playwright==1.64.1`.
- **Rationale**: All resolved and imported together in a clean 3.13.18 environment. Python
  3.13 avoids the CPython 3.10.0 dataclass `slots=True` defect that crashes pytest 9.x
  (reproduced during the Phase 1 audit). Exact pins make the lint gate's rule set and test
  behaviour reproducible.
- **Alternatives considered**: Python 3.14/3.15 (newer than needed; less wheel history);
  Python 3.10 (machine has 3.10.0 with the interpreter defect); unpinned requirements (the audit
  showed Ruff's default rules and pytest behaviour drift between releases).

## R2. google-genai version

- **Decision**: Pin `google-genai==2.33.0`.
- **Rationale**: 2.33.0 is the version in the environment that produced the saved Part 1B
  evaluation reports. A probe on both 2.33.0 and 3.0.0 showed identical behaviour for every API
  the reviewer uses: `GenerateContentConfig` with `response_mime_type`/`response_schema`,
  `errors.ClientError`/`errors.ServerError` (both subclasses of `errors.APIError`, exposing
  `.code` and `.status`). 3.0.0 emits `SyntaxWarning: invalid escape sequence` at import on
  Python 3.13; 2.33.0 does not.
- **Alternatives considered**: 3.0.0 (no functional gain, noisy import, breaks parity with the
  recorded evidence).
- **Coordination**: Part 1B's own `requirements.txt` will be pinned to the same version in
  Part 1B's separate stabilisation cycle so the portal and the Part 1B harness run identical code.

## R3. Loading the Part 1A and Part 1B backends in one process

- **Decision**: Load by file path with `importlib.util.spec_from_file_location` under unique
  module names: `Part-1A/src/limiter.py` as `part1a_limiter`; `Part-1B/.harness/evaluate.py` as
  `part1b_evaluate`. Importing `evaluate.py` imports the reviewer itself (as top-level
  `reviewer`), so the portal uses `part1b_evaluate.analyze_code`, `.MODEL`, `.RESPONSE_SCHEMA`,
  `.invariant_check` and `.validate` from one load. Set `sys.dont_write_bytecode = True` while
  loading so no `__pycache__` is written under `Part-1A/` or `Part-1B/` (Constitution I).
- **Rationale**: Probe confirmed both modules load side by side, `evaluate.analyze_code is
  reviewer.analyze_code`, and nothing in `evaluate.main()` runs at import. Part 1A's tests import
  `src.limiter` and Part 1B inserts `Part-1B/src` on `sys.path`; unique names avoid any `src`
  package collision.
- **Known side effect**: `evaluate.py` prepends `Part-1B/src` to `sys.path` at import. Harmless
  (only `reviewer.py` lives there) and documented.
- **Alternatives considered**: Adding both `src/` folders to `sys.path` (name collision risk);
  copying code into `web-demo` (violates Constitution I); running each part as a subprocess
  service (more moving parts, no benefit for a local demo).

## R4. Part 1A request handling

- **Decision**: `async def` endpoint calls `RateLimiter.check_request` directly. On
  `HTTPException` it returns a JSON response with the exception's **own** `status_code` and
  `headers` (so `Retry-After` is exactly what Part 1A produced) plus display fields. Registered
  tier is derived (display only) by matching the bucket's `capacity` against `TIERS`. Reset
  replaces the shared `RateLimiter` instance with a new one. Tier and client ID are validated
  before the limiter is called.
- **Rationale**: `TokenBucket` has no locking; an `async def` endpoint runs on the single event
  loop thread, so bucket updates are serialised without modifying Part 1A. Replacing the instance
  resets state without touching limiter logic or `TIERS`.
- **Alternatives considered**: Sync endpoint (thread pool would race on bucket state); letting
  FastAPI's default handler emit the 429 (body would lack registered tier and tokens); a
  per-client reset (unneeded for the demo; spec requires reset-all).

## R5. Part 1B outcome classification

Probe results (fake client at the SDK boundary, both SDK versions):

| Condition | Raised by reviewer / SDK | Portal category | HTTP |
|---|---|---|---|
| Blank/whitespace code | (rejected by portal before call) | `invalid_input` | 422 |
| Code longer than 20,000 chars | (rejected by portal before call) | `invalid_input` | 422 |
| Body larger than 64 KB | (rejected by middleware) | `payload_too_large` | 413 |
| `GEMINI_API_KEY` absent | portal pre-check (reviewer would raise `RuntimeError`) | `not_configured` | 503 |
| Key rejected (401/403) | `errors.ClientError` code 401/403 | `not_configured` | 503 |
| Quota / rate limit | `errors.ClientError` code 429 | `quota` | 429 |
| Other 4xx | `errors.ClientError` | `service_error` | 502 |
| 5xx | `errors.ServerError` | `service_error` | 502 |
| No response in 60 s | `asyncio.TimeoutError` (portal) | `network_timeout` | 504 |
| Transport failure | `httpx.TransportError` | `network_timeout` | 504 |
| Empty model text | `RuntimeError("Gemini returned an empty response.")` | `invalid_model_output` | 502 |
| Non-JSON / schema-invalid model text | `ValueError` from reviewer validation | `invalid_model_output` | 502 |
| Another analysis running | portal lock | `busy` | 409 |

- **Decision**: Classify by exception type and `.code`, never by parsing message text, except
  that the missing-key case is detected by checking the environment before calling the reviewer.
  Client-facing messages are fixed strings per category; SDK messages are never returned.
- **Rationale**: Probe showed SDK exception strings embed raw response JSON; fixed messages keep
  responses safe (Constitution III/IV) and categories distinct (Constitution V).

## R6. Bounding model latency

- **Decision**: Run `analyze_code` via `asyncio.to_thread` wrapped in
  `asyncio.wait_for(..., timeout=60)`. On timeout the client receives `network_timeout`; the
  worker thread is abandoned and finishes in the background. A single `asyncio.Lock` allows one
  analysis at a time and is released when the request ends (including on timeout).
- **Rationale**: The reviewer builds its own `genai.Client()` without a timeout; changing that
  would require modifying Part 1B or writing its private `_client` (Constitution I).
- **Alternatives considered**: Injecting a client with `HttpOptions(timeout=...)` into
  `reviewer._client` (rejected for production code; used only as a test double, see R8).

## R7. Live Layer 1 / Layer 2 checks (clarification 2026-11-06)

- **Decision**: After a successful analysis, run `part1b_evaluate.validate(instance=output,
  schema=part1b_evaluate.RESPONSE_SCHEMA)` (Layer 1) and
  `part1b_evaluate.invariant_check(output, code)` (Layer 2); report Layer 3 as not applicable.
- **Rationale**: Uses the harness's own schema and invariant function; nothing is
  re-implemented. Probe: valid output passes both; fabricated evidence yields
  `Finding 1: evidence is not an exact source excerpt.`
- **Note**: The reviewer validates the response before returning it, so most schema violations
  surface as `invalid_model_output` before the live checks run. The live Layer 2 evidence
  check is the one most likely to catch a real problem. This is stated in the UI.

## R8. Test double for Gemini

- **Decision**: In tests only, replace the reviewer's cached SDK client (`reviewer._client`)
  with a fake whose `models.generate_content` returns canned text or raises real
  `google.genai.errors` exceptions. The real prompt construction, response parsing and
  `_validate_response` still execute.
- **Rationale**: This is the network boundary from the application's point of view
  (Constitution VII). Probe confirmed the fake receives the real model name, prompt (containing
  the submitted code) and JSON MIME configuration.

## R9. Web security controls

- **Decisions** (each verified or standard):
  - `TrustedHostMiddleware` for `127.0.0.1` and `localhost` (probe: foreign `Host` → 400),
    mitigating DNS-rebinding access to the local API.
  - Same-origin check on POST: if an `Origin` header is present it must equal the request's own
    origin, else 403 `forbidden_origin`.
  - JSON-only bodies: probe confirmed FastAPI rejects a JSON payload sent as `text/plain` (422),
    so cross-site "simple" requests cannot reach the endpoints.
  - Custom `RequestValidationError` handler: probe confirmed the default 422 body **echoes the
    submitted input**; the portal returns `{error: {category, message, fields}}` without input.
  - Pure ASGI body-size limit of 64 KB (Content-Length and streamed bodies).
  - Headers on every response: `Content-Security-Policy: default-src 'self'; script-src 'self';
    style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none';
    base-uri 'none'; frame-ancestors 'none'; form-action 'none'`, `X-Content-Type-Options:
    nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`; `Cache-Control: no-store`
    on `/api/*`.
  - Catch-all exception handler returns `internal_error` with a fixed message.
  - Logging middleware records method, path (no query), status and duration only; Uvicorn
    access log disabled.
  - Swagger UI and ReDoc disabled (they load third-party CDN scripts, violating the CSP and
    offline rule); `/api/openapi.json` remains available.

## R10. Frontend approach

- **Decision**: One `index.html` with six sections switched by URL hash; ES modules
  (`<script type="module">`, no bundler); one stylesheet with light/dark design tokens; system
  font stacks; inline SVG icons in markup. All dynamic content built with `createElement` and
  `textContent`. An automated test fails the build if any static JavaScript contains
  `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval(` or `new Function`.
- **Rationale**: Meets Constitution IV/VI (no build step, no CDN, CSP without `unsafe-inline`).
- **Alternatives considered**: A framework (React/Vue) needs a build or CDN; Jinja templates add
  a dependency without benefit because all dynamic data arrives from the JSON API.

## R11. Test strategy

- **Decision**: Pytest + FastAPI `TestClient` (with `httpx2`) for all API, security and
  evidence tests against the real Part 1A limiter and real Part 1B code with the R8 double.
  Browser end-to-end tests with Playwright driving the installed Microsoft Edge
  (`channel="msedge"`, Edge 156 present), so no browser download is needed. A manual live Gemini
  check is recorded separately because automated tests must not depend on quota.
- **Rationale**: Covers SC-003, SC-005, SC-006, SC-007 and SC-009 automatically; covers SC-004
  with a recorded manual check.
- **Alternatives considered**: Selenium (extra driver management); no browser tests (SC-007 and
  SC-009 would rest on inspection only).

## R12. Harness and evidence format

- **Decision**: `web-demo/.harness/run.ps1` runs Ruff, Bandit, Pytest (API) and Pytest (E2E)
  and saves, per run, `web-demo/evidence/harness-results/<YYYYMMDD-HHMMSS>/summary.json` plus
  one transcript per gate. `summary.json`: `harness`, `timestamp_utc`, `python`, `tools`
  (name → version), `gates` (name, command, exit_code, result, transcript), `result`.
  The portal's Part 1A harness panel reads the same format from
  `Part-1A/evidence/harness-results/` (see contract `consumed-files.md`).
- **Dependency**: Part 1A's harness does not yet save results. Adding that is a Part 1A change
  made through Part 1A's own SDD cycle; until then the panel shows "no saved harness results".

## R13. Evaluation data presentation

- **Decision**: The dashboard reads `Part-1B/evidence/eval-results.json` as the current report
  and every `Part-1B/evidence/eval-results-run-*.json` as history, sorted by `timestamp_utc`.
  Case inputs and expected categories from `Part-1B/evals/dataset.json` are joined **only for
  the current report**.
- **Rationale**: A probe on 2026-11-07 checked every saved finding's evidence against today's
  dataset: run 1 used earlier inputs for cases 6 and 12; runs 2-4 used an earlier input for case
  6; run 5 and the current report match today's dataset. Joining today's inputs to older runs
  would misrepresent them, so history rows show summaries only.

## R14. Startup on Windows

- **Decision**: `web-demo/start.ps1` finds Python 3.13 (`py -3.13`, then `python3.13` on PATH,
  then `python` if it reports 3.13), creates `web-demo/.venv` if missing, installs
  `requirements.txt`, prints whether `GEMINI_API_KEY` is configured (never its value), and runs
  `uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log`. Parameters: `-Port`,
  `-NoBrowser`.
- **Rationale**: Probe showed `py -3.13` does not find uv-managed Pythons (registered under the
  `Astral` tag), so a fallback order is needed. One command satisfies FR-053 and SC-008.

## R15. Evidence serving

- **Decision**: Evidence items are served by opaque IDs from an allow-list built in code
  (explicit paths plus three fixed glob patterns: `Part-1B/evidence/eval-results*.json`, and the
  two `harness-results/*/` folders). Only existing UTF-8 text files up to 1 MB are listed.
  Content is returned decoded as UTF-8 without stripping a BOM, with the SHA-256 of the raw
  bytes, so byte identity is verifiable.
- **Rationale**: ID lookup makes path traversal impossible by construction (FR-041).
