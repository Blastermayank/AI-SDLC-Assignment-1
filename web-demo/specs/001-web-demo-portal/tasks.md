---

description: "Task list for the Assignment 1 web demonstration portal"
---

# Tasks: Assignment 1 Web Demonstration Portal

**Input**: Design documents from `web-demo/specs/001-web-demo-portal/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (http-api.md,
consumed-files.md, ui.md), quickstart.md

**Tests**: Required. Constitution Principle VII mandates that every functional requirement maps
to an automated test or a recorded manual check, so test tasks are included and are written
before the implementation they verify.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story from spec.md (US1-US5)
- All paths are relative to the repository root `Assignment-1/`

## Path Conventions

Web application in `web-demo/`: backend package `web-demo/app/`, static frontend
`web-demo/static/`, tests `web-demo/tests/`. Part 1A and Part 1B are read-only dependencies and
MUST NOT be modified by any task in this file (Constitution I).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, pinned dependencies, tool configuration

- [X] T001 Create the directory skeleton from plan.md: `web-demo/app/routes/`, `web-demo/static/css/`, `web-demo/static/js/`, `web-demo/static/img/`, `web-demo/tests/fixtures/`, `web-demo/tests/e2e/`, `web-demo/.harness/`, `web-demo/evidence/harness-results/` (add `.gitkeep` to empty folders) and empty `web-demo/app/__init__.py`, `web-demo/app/routes/__init__.py`
- [X] T002 [P] Create `web-demo/requirements.txt` with exact runtime pins from research R1: `fastapi==0.162.0`, `starlette==1.10.0`, `uvicorn==0.54.0`, `pydantic==2.14.3`, `google-genai==2.33.0`, `httpx==0.28.1`, `jsonschema==4.26.0`
- [X] T003 [P] Create `web-demo/requirements-dev.txt` containing `-r requirements.txt` plus `pytest==9.2.0`, `httpx2==2.16.0`, `ruff==0.17.4`, `bandit==1.9.4`, `playwright==1.64.1`
- [X] T004 [P] Create `web-demo/pyproject.toml` with: `[tool.ruff]` `target-version = "py313"`, `line-length = 100`, explicit `lint.select = ["E", "W", "F", "I", "UP", "B", "S", "SIM", "C4", "PT", "RUF", "PL"]`, `lint.per-file-ignores` for `tests/**` = `["S101", "PLR2004"]`; `[tool.pytest.ini_options]` `testpaths = ["tests"]`, marker `e2e: browser tests (Playwright + Edge)`, `addopts = "-p no:cacheprovider"`; `[tool.bandit]` `exclude_dirs = ["tests", ".venv"]`
- [X] T005 Create the local environment `web-demo/.venv` with CPython 3.13.18 and install `web-demo/requirements-dev.txt`; confirm `python -c "import fastapi, google.genai, jsonschema, playwright"` succeeds (environment only, not committed; `.venv/` is already ignored by the root `.gitignore`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: App factory, backend loading, error envelope, security middleware, page shell,
shared test fixtures. Every user story depends on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for the foundation (write first; they fail until T011-T020 exist)

- [X] T006 Create shared fixtures in `web-demo/tests/conftest.py`: `settings` (real repository root), `app` and `client` (`TestClient(create_app(settings), base_url="http://127.0.0.1:8000")`), `sentinel_key` (monkeypatched `GEMINI_API_KEY="SENTINEL-KEY-7d41b0c9-do-not-leak"`), `no_key` (deletes `GEMINI_API_KEY`), `fake_gemini` factory that installs a fake SDK client into the loaded reviewer module's `_client` (via `sys.modules["reviewer"]`) whose `models.generate_content(**kw)` records `kw` and returns an object with `.text` or raises a supplied exception, restoring the original `_client` afterwards (research R8), and `copy_part1b_evidence(tmp_path)` that copies `Part-1B/evidence/` and `Part-1B/evals/` into a temporary repository root
- [X] T007 [P] Write `web-demo/tests/test_health.py`: `GET /api/health` returns exactly the contract shape including a UUID `server_instance` that is stable across calls; `part1b.configured` is `true` with `sentinel_key` and `false` with `no_key`; response text never contains the sentinel or its length; `repository_url` is `null` for a missing or non-GitHub value in a temporary `portal-config.json` and echoes a valid `https://github.com/<owner>/<repo>` value (FR-004)
- [X] T008 [P] Write `web-demo/tests/test_security.py`: every response from `/` and `/api/health` carries the exact CSP from research R9 plus `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`; `/api/*` responses carry `Cache-Control: no-store`; `Host: evil.example` → 400; POST with `Origin: http://evil.example` → 403 `forbidden_origin`; a 70,000-byte JSON body → 413 `payload_too_large`; a 422 body never contains the submitted value; a route forced to raise (test-only router) → 500 `internal_error` with no traceback text; `/docs` and `/redoc` → 404; `/api/openapi.json` → 200
- [X] T009 [P] Write `web-demo/tests/test_backends.py`: loaded modules are named `part1a_limiter` and `part1b_evaluate`; `part1b_evaluate.analyze_code is sys.modules["reviewer"].analyze_code`; loading creates no `__pycache__` directory under `Part-1A/` or `Part-1B/` (compare directory listings before/after in a copied tree); a missing backend path raises a clear startup error
- [X] T010 [P] Create the browser test harness in `web-demo/tests/e2e/conftest.py`: session `live_server` fixture running `uvicorn.Server` for `create_app()` in a background thread on a free `127.0.0.1` port; `browser` fixture via Playwright `chromium.launch(channel="msedge", headless=True)`; `page` fixture that fails the test on any `pageerror` and on any console error except Chromium's `Failed to load resource: the server responded with a status of NNN` for `/api/*` requests whose status the test registered as expected via an `expect_api_status(*codes)` helper (research R16); reuse `fake_gemini` so no live model call is made; mark all tests `e2e`

### Implementation for the foundation

- [X] T011 Implement `web-demo/app/config.py`: frozen `Settings` dataclass with `repo_root` (default: parent of `web-demo/`, overridable by `WEB_DEMO_REPO_ROOT`), derived Part 1A/1B paths, `max_body_bytes = 65536`, `max_code_chars = 20000`, `analysis_timeout_s = 60.0`, `client_id_pattern = r"^[A-Za-z0-9_.-]{1,64}$"`, `allowed_hosts = ["127.0.0.1", "localhost"]`, `max_evidence_bytes = 1_048_576`, `repository_url` read from `web-demo/portal-config.json` and kept only if it matches `^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$` (else `None`); create `web-demo/portal-config.json` with `{"repository_url": null}`; never reads or stores the API key value
- [X] T012 Implement `web-demo/app/backends.py`: `load_backends(settings)` loads `Part-1A/src/limiter.py` as `part1a_limiter` and `Part-1B/.harness/evaluate.py` as `part1b_evaluate` with `importlib.util.spec_from_file_location`, registering each in `sys.modules`, with `sys.dont_write_bytecode = True` during loading and restored afterwards (research R3); returns a `Backends` object exposing `limiter_module`, `evaluate_module`, `reviewer_module`
- [X] T013 [P] Implement `web-demo/app/errors.py`: the 12 categories from data-model.md (`invalid_input`, `payload_too_large`, `forbidden_origin`, `not_found`, `busy`, `not_configured`, `quota`, `service_error`, `network_timeout`, `invalid_model_output`, `report_unavailable`, `internal_error`) with fixed messages and HTTP statuses; `PortalError(category, fields=None)`; `error_response()` building `{"error": {"category", "message", "fields"?}}`; handlers for `PortalError`, `RequestValidationError` (field names only, never values), Starlette `HTTPException` (404/405 → `not_found`) and `Exception` (→ `internal_error`, logs exception type and path only)
- [X] T014 [P] Implement `web-demo/app/security.py` as pure ASGI middlewares: `BodySizeLimitMiddleware` (reject when `Content-Length` > 65536 or streamed bytes exceed it → 413 `payload_too_large`), `SameOriginMiddleware` (POST with an `Origin` header not equal to `scheme://host` of the request → 403 `forbidden_origin`), `SecurityHeadersMiddleware` (CSP `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'`, `nosniff`, `no-referrer`, `DENY`, plus `Cache-Control: no-store` for `/api/*`), `RequestLogMiddleware` (logger `web_demo.access`: method, path without query string, status, duration in ms; nothing else)
- [X] T015 Implement `web-demo/app/main.py` `create_app(settings=None)`: `FastAPI(docs_url=None, redoc_url=None, openapi_url="/api/openapi.json")`; add `TrustedHostMiddleware(allowed_hosts=settings.allowed_hosts)` and the T014 middlewares; register T013 handlers; call `load_backends` and store results plus `app.state.limiter = RateLimiter()`, `app.state.analysis_lock = asyncio.Lock()` and `app.state.server_instance = str(uuid.uuid4())`; mount `web-demo/static` at `/static`; `GET /` returns `static/index.html`; module-level `app = create_app()` for Uvicorn (implemented as the factory `create_app` run with `uvicorn app.main:create_app --factory`, so importing the module has no side effects)
- [X] T016 Implement `web-demo/app/routes/health.py` `GET /api/health` per contracts/http-api.md (FR-054): `part1b.configured = bool(os.environ.get("GEMINI_API_KEY", "").strip())`, `model` from `part1b_evaluate.MODEL`, `server_instance` from `app.state`, `repository_url` from settings; include the router in `web-demo/app/main.py`
- [X] T017 Create the page shell `web-demo/static/index.html`: `<header>` with title, `#health-badge`, `#theme-toggle`; `<nav>` with six links (hashes from contracts/ui.md); `<main>` with six `<section>` elements `section-overview`, `section-methodology`, `section-part-1a`, `section-part-1b`, `section-evaluation`, `section-evidence`, each with its heading; skip-to-content link; `<noscript>` message; `<link rel="icon" href="/static/img/icon.svg" type="image/svg+xml">` plus the file `web-demo/static/img/icon.svg`; `<footer>` with `#repo-link`; single `<script type="module" src="/static/js/app.js">`; no inline scripts, no `style` attributes, no external URLs
- [X] T018 [P] Create `web-demo/static/css/portal.css`: design tokens on `:root` for light and dark (`prefers-color-scheme` plus `[data-theme]` override); system UI and monospace font stacks; layout (sidebar navigation ≥ 1024 px, top navigation below); components: card, status badge (pass/fail/warn/info/neutral), table, buttons, inputs, `<pre>` code blocks with wrapping, details/summary; visible `:focus-visible`; WCAG AA contrast; no horizontal page scroll from 360 px width
- [X] T019 [P] Create `web-demo/static/js/dom.js` (safe builders: `el(tag, {className, attrs, text}, children)` using `textContent` only, `clear(node)`, `formatPercent(value, 1)`, `formatTimestamp(iso)`) and `web-demo/static/js/api.js` (`request(method, path, body)` returning `{ok, status, headers, data}` for every HTTP status, mapping fetch failures to `{ok: false, status: 0, data: {error: {category: "network_timeout"}}}` and guarding JSON parsing)
- [X] T020 Create `web-demo/static/js/app.js`: hash router showing exactly one section and setting `aria-current="page"`; default `#overview`; theme toggle persisting to `localStorage` inside try/catch; health badge populated from `/api/health` ("Gemini configured" / "Gemini not configured"); `#repo-link` and `#overview-repo-link` set from `repository_url` (anchor `href` only for the validated URL, otherwise the text "Repository link not configured"); exports the last-seen `server_instance` for section modules; imports each section module's `init()` as they are added

**Checkpoint**: `pytest web-demo/tests -m "not e2e"` passes T007-T009; `GET /` renders the shell.

---

## Phase 3: User Story 1 - Demonstrate tiered rate limiting live (Priority: P1) 🎯 MVP

**Goal**: Real Part 1A decisions over HTTP with 429 + `Retry-After`, history, tier info, reset,
validation and the saved-harness panel (FR-010 to FR-017).

**Independent Test**: Six Free-tier requests for a new client ID: five 200s then a 429 with a
`Retry-After` of at least 1 second (quickstart V1).

### Tests for User Story 1 (write first, confirm they fail)

- [ ] T021 [P] [US1] Write `web-demo/tests/test_part1a_api.py`: `/api/part-1a/tiers` equals `part1a_limiter.TIERS` (capacity; `refill_per_minute == refill_rate * 60`); parametrised over 10 fresh client IDs (SC-002): 5 Free requests → 200 `accepted: true` with `server_instance` equal to `/api/health`'s; 6th → HTTP 429 whose `Retry-After` header equals the header on the `HTTPException` raised by Part 1A (captured with a spy on `RateLimiter.check_request`) and `retry_after_seconds == int(header) >= 1`; client isolation; tier mismatch (first `free`, then `premium` → `tier_mismatch: true`, `registered_tier: "free"`, `capacity: 5`); reset → `clients_cleared` count then next request accepted; invalid inputs `""`, 65 characters, `"bad id!"`, `"../x"`, tier `"gold"`, missing tier → 422 `invalid_input` with `fields` and `app.state.limiter.clients` unchanged; the limiter on `app.state` is an instance of `part1a_limiter.RateLimiter`
- [ ] T022 [P] [US1] Write `web-demo/tests/test_harness_results.py` for `app/harness_results.py`: empty or missing results directory → `available: false`; two run folders → latest by folder name; transcripts read only when named in `summary.json` and resolving inside the run folder (a `"transcript": "../../README.md"` entry is ignored); malformed `summary.json` skipped; files over 1 MB not read; `/api/part-1a/harness` returns the reader output
- [ ] T023 [P] [US1] Write `web-demo/tests/e2e/test_part1a_ui.py`: on `#part-1a`, six clicks of `#rl-send` with client `e2e-client` / Free → `#rl-history` has 6 rows (newest first), first row shows `429` and a retry delay, `#rl-last-outcome` announces REJECTED; selecting Premium for the same client shows `#rl-tier-warning`; `#rl-reset` empties history; client ID `bad id!` is sent to the server and its 422 validation message is shown with no row added; after changing `app.state.server_instance` on the live server, the next request clears the old rows and shows the "server restarted" notice; `#rl-tiers` lists 3 tiers

### Implementation for User Story 1

- [ ] T024 [US1] Add `RateLimitRequest` to `web-demo/app/schemas.py`: `client_id` "1-64 chars, regex `^[A-Za-z0-9_.-]{1,64}$`"; `tier` string validated in the route as "Exactly one of the `Tier.name` values" (keys of `part1a_limiter.TIERS`, not a copied list); plus `RateLimitOutcome` response model with the fields in data-model.md
- [ ] T025 [US1] Implement `web-demo/app/harness_results.py` `latest_run(results_dir, max_bytes)` per contracts/consumed-files.md (latest valid `summary.json`, transcripts restricted to files named in it inside the run folder, size cap)
- [ ] T026 [US1] Implement `web-demo/app/routes/part1a.py` as `async def` handlers (research R4): `GET /api/part-1a/tiers`; `POST /api/part-1a/request` calling `app.state.limiter.check_request(client_id, tier)`, on `HTTPException` returning `JSONResponse(status_code=exc.status_code, headers=exc.headers, content=outcome)`, deriving `registered_tier` by matching bucket `capacity` to `TIERS`, `tokens_remaining` rounded to 3 decimals, `server_instance` from `app.state`; `POST /api/part-1a/reset` replacing `app.state.limiter` with a new `RateLimiter()`; `GET /api/part-1a/harness` reading `Part-1A/evidence/harness-results/`; include the router in `web-demo/app/main.py`
- [ ] T027 [US1] Fill `section-part-1a` in `web-demo/static/index.html`: problem statement; intended behaviour; token-bucket explanation (capacity, refill over time, one token per request, rejection with retry delay); `#rl-tiers` table; form with `#rl-client-id` (default `demo-client`, `maxlength=64`), `#rl-tier`, `#rl-send`, `#rl-reset`; `#rl-last-outcome` (`aria-live="polite"`); `#rl-tier-warning` (hidden); `#rl-history` table; `#rl-harness` panel; known limitations (in-memory state lost on restart; not shared across processes; tier fixed at first request; Part 1A falls back to Free for unknown tiers, which the portal blocks)
- [ ] T028 [US1] Implement `web-demo/static/js/part1a.js` and register it in `web-demo/static/js/app.js`: load tiers; send one request per click (button disabled while pending); render outcome, history row, tier warning and tokens remaining strictly from the server response (status 429 rendered as an expected outcome, `Retry-After` read from the response header); reset; every submission (including an invalid client ID) is sent to the server and the displayed validation message is the server's 422 (no client-side blocking, Constitution V); clear history and show a "server restarted" notice when a response's `server_instance` differs from the last seen value; harness panel showing per-gate result, timestamp, and transcripts in collapsible `<pre>` blocks, or "No saved harness results"

**Checkpoint**: T021-T023 pass; quickstart V1-V5 work in the browser.

---

## Phase 4: User Story 2 - Review source code with the live Gemini model (Priority: P2)

**Goal**: Live analysis through the existing reviewer with findings, raw JSON, live Layer 1/2
checks and classified failures (FR-020 to FR-028).

**Independent Test**: Submit the SQL-injection sample and see rendered findings from a live call
(quickstart V6), and every failure category with the fake client.

### Tests for User Story 2 (write first, confirm they fail)

- [ ] T029 [P] [US2] Write `web-demo/tests/test_part1b_api.py` using `fake_gemini`: valid findings → 200 with `model == part1b_evaluate.MODEL`, integer `elapsed_ms`, `result == json.loads(raw)`, Layer 1 and Layer 2 passed, Layer 3 `applicable: false`; the fake received `model == MODEL` and a prompt containing the submitted code; fabricated evidence → Layer 2 failed with `"Finding 1: evidence is not an exact source excerpt."`; empty findings → 200 with `findings == []`; blank code and 20,001-character code → 422 `invalid_input` and the fake was not called; `no_key` → 503 `not_configured` and the fake was not called; `errors.ClientError(429, ...)` → 429 `quota`; `ClientError(403, ...)` → 503 `not_configured`; `ClientError(400, ...)` → 502 `service_error`; `errors.ServerError(503, ...)` → 502 `service_error`; `httpx.ConnectError` → 504 `network_timeout`; a fake that sleeps longer than a test-overridden 0.2 s timeout → 504 `network_timeout`; non-JSON text and empty text → 502 `invalid_model_output`; lock already held → 409 `busy`; a finding description `<img src=x onerror=alert(1)>` is returned verbatim; no response body contains SDK exception text or the sentinel key; FR-024: submitting code containing a unique marker leaves the file listing of the repository root (excluding `.venv`) unchanged and the marker absent from all captured log records
- [ ] T030 [P] [US2] Write `web-demo/tests/e2e/test_part1b_ui.py` with the fake client: `#rv-analyze` disabled for empty/whitespace input; loading a sample and analysing renders one card per finding with all five fields and a severity badge; a description containing `<img src=x onerror=alert(1)>` appears as literal text, no `img` element is created inside `#rv-findings` and no dialog fires; `#rv-live-checks` shows Layer 1/2 PASS and Layer 3 not applicable; `#rv-raw` contains the raw JSON; a quota error shows the quota message and no findings; `#rv-count` updates

### Implementation for User Story 2

- [ ] T031 [US2] Add `ReviewSubmission` to `web-demo/app/schemas.py`: `code` "1-20,000 characters and not whitespace-only" (validator rejects `code.strip() == ""`); plus `ReviewResult` response model (`model`, `elapsed_ms`, `result`, `raw`, `live_checks`)
- [ ] T032 [US2] Implement `web-demo/app/routes/part1b.py` `POST /api/part-1b/analyze` (research R5-R7): if `app.state.analysis_lock.locked()` → `busy`; if `GEMINI_API_KEY` unset/blank → `not_configured` without calling the reviewer; otherwise `asyncio.wait_for(asyncio.to_thread(part1b_evaluate.analyze_code, code), settings.analysis_timeout_s)`; map exceptions by type and `.code` exactly as the R5 table, including `httpx.TransportError` → `network_timeout` (verified against the real SDK, research R5), never using exception messages in responses; on success compute Layer 1 with `part1b_evaluate.validate(instance=result, schema=part1b_evaluate.RESPONSE_SCHEMA)` and Layer 2 with `part1b_evaluate.invariant_check(result, code)`; include the router in `web-demo/app/main.py`
- [ ] T033 [US2] Fill `section-part-1b` in `web-demo/static/index.html`: problem statement; how Gemini is used (model name, structured JSON with a response schema, temperature 0.1); why output is non-deterministic; input instructions (paste source code, up to 20,000 characters, never executed); output schema table (status, findings; five finding fields; severities High/Medium/Low); guardrails (untrusted input, embedded instructions ignored, exact evidence excerpts, at most 10 findings); `#rv-samples` buttons (SQL injection, command injection, hardcoded credential, benign function); `#rv-code`, `#rv-count`, `#rv-analyze`, `#rv-status` (`aria-live="polite"`), `#rv-findings`, `#rv-live-checks`, `#rv-raw`; disclaimer (suggestions, not proof of security; results vary between calls); known limitations
- [ ] T034 [US2] Implement `web-demo/static/js/part1b.js` and register it in `web-demo/static/js/app.js`: sample loading (no auto-submit); character counter; analyse with a loading state and the button disabled until the response arrives; findings cards; "Analysis completed: no findings reported (this does not prove the code is secure)" for empty findings; live-check panel; raw JSON in `<details>`; error panel per category using fixed client-side messages keyed by `error.category`

**Checkpoint**: T029-T030 pass; quickstart V6-V8 work (V6 with one live call).

---

## Phase 5: User Story 3 - Inspect the saved Part 1B evaluation (Priority: P3)

**Goal**: Read-only dashboard of the current saved report, case table and run history
(FR-030 to FR-033).

**Independent Test**: With the model unreachable, every dashboard figure matches
`Part-1B/evidence/eval-results.json` (quickstart V9).

### Tests for User Story 3 (write first, confirm they fail)

- [ ] T035 [P] [US3] Copy `Part-1B/evidence/eval-results.json` from commit `2c88355` to `web-demo/tests/fixtures/eval-results-reference-20261106T061902Z.json` (byte-identical, SHA-256 recorded in the test) as the reference fixture for User Story 3 scenarios 1-2
- [ ] T036 [P] [US3] Write `web-demo/tests/test_evaluation_api.py`: `/api/part-1b/evaluation` `report` equals the parsed current file on disk; with the reference fixture as the current report: `total_cases 15`, `completed_cases 15`, `passed_cases 13`, `aggregate_score` 86.666…, `threshold 80.0`, `status "PASS"`, failed ids `[3, 8]` with their recorded `error` strings; `cases` join `type`, `input`, `expected_vuln` from `dataset.json` for the current report only; `/history` lists every `eval-results-run-*.json` plus the current report sorted by `timestamp_utc` with `failed_case_ids` and the caveat text; a synthetic 16-case `INCOMPLETE` report and a missing report (`404 report_unavailable`) are handled; an unreadable history file is listed with `status "UNREADABLE"`; SHA-256 and modification times of every file in `Part-1B/evidence/` are unchanged after all calls; the fake Gemini client was never called
- [ ] T037 [P] [US3] Write `web-demo/tests/e2e/test_evaluation_ui.py`: `#ev-summary` shows the model, 15 / 15 / 13, `86.7%`, `80%`, and a PASS badge for the real current report; rows for cases 3 and 8 are marked failed at Layer 3 and expand to show input, expected category, model output and explanation; `#ev-history` row count equals the number of saved reports and the caveat text is visible

### Implementation for User Story 3

- [ ] T038 [US3] Implement `web-demo/app/routes/evaluation.py`: `GET /api/part-1b/evaluation` (read `Part-1B/evidence/eval-results.json` with `utf-8-sig`, pass content through unchanged, join dataset fields for the current report only per research R13, scoring explanation, `404 report_unavailable` if missing/invalid) and `GET /api/part-1b/evaluation/history` (RunSummary per data-model.md, ascending `timestamp_utc`, `is_current`, `UNREADABLE` entries, fixed caveat); no writes, no model calls; include the router in `web-demo/app/main.py`
- [ ] T039 [US3] Fill `section-evaluation` in `web-demo/static/index.html`: pipeline explanation (dataset → model call → Layer 1 schema → Layer 2 invariants → Layer 3 semantic category/alias matching, not an LLM judge → aggregate score → PASS/FAIL); scoring rule and declared 80% threshold; statement that figures come from one recorded run and do not guarantee model accuracy; `#ev-summary`, `#ev-cases`, `#ev-history` containers
- [ ] T040 [US3] Implement `web-demo/static/js/evaluation.js` and register it in `web-demo/static/js/app.js`: summary tiles with a status badge (PASS / FAIL / INCOMPLETE distinct); case table with L1/L2/L3 badges and expandable details (input and model output as `<pre>` text); history table with caveat; "Report unavailable" state

**Checkpoint**: T035-T037 pass; quickstart V9 works with networking disabled.

---

## Phase 6: User Story 4 - Understand the assignment and its methodology (Priority: P4)

**Goal**: Overview and methodology content, accurate to the repository, with artifact
availability shown from the evidence index (FR-001 to FR-003, FR-054 UI).

**Independent Test**: A reader answers "what are the two applications, how is each validated,
what are the limitations" from the Overview and Methodology sections alone.

### Tests for User Story 4 (write first, confirm they fail)

- [ ] T041 [P] [US4] Write `web-demo/tests/test_static_content.py`: `web-demo/static/index.html` contains `gemini-3.5-flash-lite`, the phrase "category/alias matching", the phrase "not an LLM judge", "one recorded run", both application names, the six section ids, and the limitation statements for Part 1A and Part 1B; it contains no affirmative "LLM-as-a-Judge" claim, no "100%" accuracy claim and no "mock" description of Part 1B
- [ ] T042 [P] [US4] Write `web-demo/tests/e2e/test_overview_ui.py`: default route shows `section-overview` only; every navigation link switches to its section and sets `aria-current`; with the key removed from the live server's environment the `#health-badge` reads "Gemini not configured"; with `repository_url` unset the footer reads "Repository link not configured" and with a valid URL `#repo-link` is an anchor to it; methodology stage chips mark artifacts missing from the evidence index as "not in repository" (for example Part 1A plan/tasks) and present ones as links

### Implementation for User Story 4

- [ ] T043 [US4] Fill `section-overview` in `web-demo/static/index.html`: assignment objective; what specification-driven development means in this repository; why one deterministic and one non-deterministic application; deterministic vs non-deterministic validation comparison table; role of harnesses; cards linking to every section; `#overview-repo-link` placeholder (FR-004)
- [ ] T044 [US4] Fill `section-methodology` in `web-demo/static/index.html`: workflow diagram (problem statement → constitution → specify → clarify → plan → tasks → analyze → implement → harness validation → feedback and repair → revalidation → human review) as semantic markup styled in CSS; per-part columns (Part 1A, Part 1B) with a `data-evidence-id` on each stage that names its artifact; description of Part 1A gates (Ruff, Bandit, Pytest) and Part 1B layers; statement that harness logs and the final human decision are authored by the student
- [ ] T045 [US4] Implement `web-demo/static/js/methodology.js` and register it in `web-demo/static/js/app.js`: fetch `/api/evidence` once, mark each `data-evidence-id` stage as present (link to the Evidence viewer) or "not in repository"

**Checkpoint**: T041-T042 pass; quickstart V10.

---

## Phase 7: User Story 5 - Browse engineering evidence (Priority: P5)

**Goal**: Allow-listed, grouped evidence with exact plain-text viewing (FR-040, FR-041).

**Independent Test**: Every listed item opens with content byte-identical to the repository
file (quickstart V11) and traversal attempts are refused (V12).

### Tests for User Story 5 (write first, confirm they fail)

- [ ] T046 [P] [US5] Write `web-demo/tests/test_evidence_api.py`: index lists only existing files (temporary repository root with a subset of files → absent ones omitted); groups `historical`, `portal`, `verification`; for every listed item the returned `content.encode("utf-8")` equals the file bytes and `sha256` matches `hashlib.sha256(bytes)`; unknown id → 404 `not_found`; ids `../README.md`, `..%2F..%2FREADME.md`, `%2e%2e`, `C:/Windows/win.ini`, `Part-1A/src/limiter.py` → 404; a file over 1 MB and a non-UTF-8 file are not listed; a file deleted after listing → 404
- [ ] T047 [P] [US5] Write `web-demo/tests/e2e/test_evidence_ui.py`: `#evd-groups` shows the three groups; opening the Part 1B dataset shows its path, size, SHA-256 and content in `#evd-viewer`; content containing markup is shown literally

### Implementation for User Story 5

- [ ] T048 [US5] Implement `web-demo/app/evidence_index.py`: explicit allow-list of `EvidenceItem` (`id`, `label`, `group`, `part`, `path`) covering README.md; Part 1A constitution, specify, (if present) clarify/plan/tasks, `src/limiter.py`, `tests/test_limiter.py`, `.harness/run.ps1`, `requirements.txt`, `harness-log.md`, initial and final snapshots; Part 1B constitution, specify, (if present) clarify/plan/tasks, `src/reviewer.py`, `.harness/evaluate.py`, `evals/dataset.json`, `requirements.txt`, `harness-log.md`, initial and final snapshots, `evidence/dataset-before-security-refinement.json`; portal constitution and every file in `web-demo/specs/001-web-demo-portal/`; plus the fixed patterns `Part-1B/evidence/eval-results*.json`, `Part-1A/evidence/harness-results/*/*`, `web-demo/evidence/harness-results/*/*`; list only existing UTF-8 files ≤ 1 MB (research R15)
- [ ] T049 [US5] Implement `web-demo/app/routes/evidence.py`: `GET /api/evidence` (grouped index) and `GET /api/evidence/{id}` (lookup by id only; content decoded as UTF-8 without stripping a BOM; `sha256` of raw bytes; `404 not_found` otherwise); include the router in `web-demo/app/main.py`
- [ ] T050 [US5] Fill `section-evidence` in `web-demo/static/index.html` (intro explaining the three groups and that content is shown exactly as stored; `#evd-groups`; `#evd-viewer`) and implement `web-demo/static/js/evidence.js`, registered in `web-demo/static/js/app.js`

**Checkpoint**: T046-T047 pass; quickstart V11-V12.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Start script, harness, cross-cutting safety tests, documentation, recorded
verification

- [ ] T051 [P] Write `web-demo/tests/test_static_safety.py`: no file under `web-demo/static/js/` contains `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval(` or `new Function`; `index.html` has no inline `<script>` body, no `on*=` attributes, no `style=` attributes and no `http://`/`https://` URLs; CSS has no `@import` of remote URLs (SC-007, Constitution IV/VI)
- [ ] T052 [P] Write `web-demo/tests/test_secret_sweep.py`: with `sentinel_key` set and the fake client raising each error type, call every endpoint in contracts/http-api.md and fetch every static asset; assert the sentinel string is absent from all bodies, headers and captured log records; also submit code containing a unique code marker with the fake returning output containing a unique output marker and assert neither marker, nor any request body, appears in captured log records (SC-005, FR-050, FR-055)
- [ ] T053 [P] Write `web-demo/tests/e2e/test_responsive_a11y.py`: at 360 px viewport width each section has `document.documentElement.scrollWidth <= window.innerWidth`; every interactive control is reachable with Tab and operable with Enter/Space; focus is visible; no console errors (SC-009); first page render (`performance.getEntriesByType("navigation")[0].domContentLoadedEventEnd`) under 1,000 ms (constitution performance constraint); computed text/background contrast of body text, muted text, links, buttons and status badges is at least 4.5:1 in both light and dark themes (constitution WCAG AA constraint)
- [ ] T054 [P] Write `web-demo/tests/test_performance.py`: 20 sequential calls to each non-Gemini endpoint all complete in under 200 ms on the test client (plan performance goal)
- [ ] T055 Create `web-demo/start.ps1` (research R14): locate Python 3.13 (`py -3.13`, then `python3.13`, then `python` reporting 3.13; otherwise print install instructions and exit 1); create `web-demo/.venv` if missing; install `requirements.txt`; print `Gemini API key: configured (value hidden)` or `not configured`; run `python -m uvicorn app.main:app --host 127.0.0.1 --port $Port --no-access-log` (default 8000); open the browser unless `-NoBrowser`
- [ ] T056 Create `web-demo/.harness/run.ps1` (research R12): gates `SYNTAX & LINT GUARD (RUFF)` → `ruff check app tests`, `SECURITY / SAST GUARD (BANDIT)` → `bandit -r app -ll -c pyproject.toml`, `API & CONTRACT TESTS (PYTEST)` → `python -m pytest -m "not e2e" -v`, `BROWSER E2E TESTS (PLAYWRIGHT)` → `python -m pytest -m e2e -v`; each gate's combined output saved unedited to `web-demo/evidence/harness-results/<YYYYMMDD-HHMMSS>/NN-<gate>.txt`; `summary.json` per contracts/consumed-files.md with tool versions; exit 0 only if all gates pass
- [ ] T057 [P] Write `web-demo/README.md`: purpose and scope (presentation layer only), prerequisites, start command, harness command, API summary linking contracts/http-api.md, security notes, troubleshooting (Python not found, execution policy, port in use, key not configured)
- [ ] T058 Run `web-demo/.harness/run.ps1` and commit the resulting `web-demo/evidence/harness-results/<run>/` folder unedited; if any gate fails, fix the implementation (never the tests or gates) and run again, keeping every run folder
- [ ] T059 Perform the manual live-Gemini verification in quickstart.md (at least 10 valid submissions through the running portal, per revised SC-004) and save the observed results, with timestamps and model name, to `web-demo/evidence/live-gemini-verification-<YYYYMMDD>.md`
- [ ] T060 Perform the quickstart.md fresh-start timing (SC-008), then walk through scenarios V1-V13 in Edge and record the timing and pass/fail per scenario in `web-demo/evidence/quickstart-validation-<YYYYMMDD>.md`
- [ ] T061 Add a "Web demonstration portal" section to the repository root `README.md` linking to `web-demo/README.md` (no other root README changes in this feature)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none
- **Foundational (Phase 2)**: depends on Setup; blocks all user stories
- **User Stories (Phases 3-7)**: each depends only on Foundational
- **Polish (Phase 8)**: T051-T054 and T057 can start after Foundational; T055-T056 after
  Foundational; T058-T061 after all user stories

### User Story Dependencies

- **US1 (P1)**: Foundational only. Its harness panel shows "No saved harness results" until
  Part 1A's own SDD cycle adds saved runs (plan: Dependencies on Other Work).
- **US2 (P2)**: Foundational only
- **US3 (P3)**: Foundational only
- **US4 (P4)**: Foundational; its stage chips use `/api/evidence` from US5. Without US5 every
  stage shows "not in repository", so US5 should land first if US4 is demonstrated alone.
- **US5 (P5)**: Foundational only

### Within Each User Story

- Tests are written first and must fail before implementation
- Schemas → backend helpers → routes → page markup → page script
- `web-demo/static/index.html` and `web-demo/static/js/app.js` are shared files; their edits in
  different stories are sequential, never parallel

### Parallel Opportunities

- Setup: T002, T003, T004
- Foundational tests: T007, T008, T009, T010; implementation: T013, T014, T018, T019
- Every story's test tasks are [P] with each other
- Polish: T051, T052, T053, T054, T057

---

## Parallel Example: User Story 1

```text
Task: "T021 Write web-demo/tests/test_part1a_api.py"
Task: "T022 Write web-demo/tests/test_harness_results.py"
Task: "T023 Write web-demo/tests/e2e/test_part1a_ui.py"
```

## Parallel Example: User Story 2

```text
Task: "T029 Write web-demo/tests/test_part1b_api.py"
Task: "T030 Write web-demo/tests/e2e/test_part1b_ui.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational
2. Phase 3 (US1) → run T021-T023 → validate quickstart V1-V5
3. Stop and review: the portal already demonstrates Part 1A end to end

### Incremental Delivery

1. Foundation → US1 (MVP) → US2 (live Gemini) → US3 (dashboard) → US5 (evidence) → US4
   (overview/methodology, uses the evidence index) → Polish
2. Run the `web-demo` harness after each story; commit after each task or logical group

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] labels map tasks to user stories for traceability (FR → task mapping is checked by
  `/speckit-analyze`)
- Never modify files under `Part-1A/` or `Part-1B/` in this feature; Part 1A/1B changes go
  through their own SDD cycles
- Never weaken, skip or delete a test or gate to obtain a pass; record every harness run
- Harness-log entries and the final ACCEPT/REJECT decision are written by the repository owner
