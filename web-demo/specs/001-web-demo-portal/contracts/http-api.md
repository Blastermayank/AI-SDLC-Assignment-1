# Contract: Portal HTTP API

**Feature**: `001-web-demo-portal` | **Base URL**: `http://127.0.0.1:8000` | **Format**: JSON (UTF-8)

General rules (all endpoints):

- Request bodies MUST be `application/json` and at most 64 KB (larger → 413
  `payload_too_large`).
- POST requests carrying an `Origin` header that differs from the server's own origin → 403
  `forbidden_origin`. Requests with a `Host` other than `127.0.0.1` or `localhost` → 400.
- Errors use the ErrorEnvelope (`{"error": {"category", "message", "fields"?}}`, see
  [data-model.md](../data-model.md)), except Part 1A's 429, which is a rate-limit **outcome**.
- Validation failures never echo submitted values.
- Every response carries the security headers in research R9; `/api/*` responses add
  `Cache-Control: no-store`.
- No response, header or log line ever contains the value of `GEMINI_API_KEY`.

---

## GET `/api/health` *(FR-054)*

200:

```json
{
  "status": "ok",
  "server_instance": "3f6c2a9e-1b7d-4e0a-9c55-0d2f7b8e4a11",
  "repository_url": null,
  "part1a": { "available": true },
  "part1b": { "module_loaded": true, "configured": false, "model": "gemini-3.5-flash-lite" }
}
```

`configured` is `true` only when `GEMINI_API_KEY` is set to a non-empty value. No value or
length of the key is returned. `server_instance` is a random UUID generated at server start
(FR-013). `repository_url` comes from `web-demo/portal-config.json` and is `null` unless it
matches `^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$` (FR-004).

---

## GET `/api/part-1a/tiers` *(FR-010)*

200: array ordered free, standard, premium.

```json
[{ "name": "free", "capacity": 5, "refill_per_second": 0.0833333, "refill_per_minute": 5.0 }]
```

## POST `/api/part-1a/request` *(FR-011 to FR-016)*

Request: `{ "client_id": "demo-client", "tier": "free" }`

| Status | When | Body | Headers |
|---|---|---|---|
| 200 | Limiter accepted the request | RateLimitOutcome, `accepted: true`, `retry_after_seconds: null` | — |
| 429 | Limiter raised `HTTPException(429)` | RateLimitOutcome, `accepted: false`, `retry_after_seconds` = int(header), `detail` | `Retry-After` exactly as produced by Part 1A |
| 422 | Invalid `client_id` or `tier` | ErrorEnvelope `invalid_input`, `fields` | — |

Any other status code raised by the limiter is passed through with its own status and headers.
Every outcome body includes `server_instance` (same value as `/api/health`).

## POST `/api/part-1a/reset` *(FR-015)*

Request: `{}` → 200 `{ "reset": true, "clients_cleared": 3 }`. Tier configuration is unchanged.

## GET `/api/part-1a/harness` *(FR-017)*

200 with the latest saved Part 1A HarnessRunSummary plus each gate's transcript text:

```json
{ "available": true, "run": "20261107-101500", "summary": { "...": "..." },
  "transcripts": { "SYNTAX & LINT GUARD (RUFF)": "All checks passed!\n" } }
```

200 `{ "available": false }` when no saved run exists. The portal never executes the harness.

---

## POST `/api/part-1b/analyze` *(FR-020 to FR-028)*

Request: `{ "code": "query = f'SELECT * FROM users WHERE id = {user_id}'" }`

| Status | Category | When |
|---|---|---|
| 200 | — | ReviewResult (see data model) |
| 422 | `invalid_input` | `code` missing, not a string, blank/whitespace-only, or longer than 20,000 characters |
| 409 | `busy` | Another analysis is in progress |
| 503 | `not_configured` | Key absent, or rejected by the service (401/403) |
| 429 | `quota` | Service returned 429 |
| 502 | `service_error` | Other service 4xx or any 5xx |
| 504 | `network_timeout` | No result within 60 s, or transport failure |
| 502 | `invalid_model_output` | Empty, non-JSON or contract-violating model output |

200 example:

```json
{
  "model": "gemini-3.5-flash-lite",
  "elapsed_ms": 2140,
  "result": { "status": "success", "findings": [ { "vulnerability": "SQL Injection",
    "severity": "High", "description": "...", "evidence": "SELECT * FROM users WHERE id = {user_id}",
    "remediation": "..." } ] },
  "raw": "{\"status\": \"success\", \"findings\": [...]}",
  "live_checks": {
    "layer1": { "passed": true, "errors": [] },
    "layer2": { "passed": true, "errors": [] },
    "layer3": { "applicable": false, "reason": "Requires ground truth; evaluated only on the dataset." }
  }
}
```

---

## GET `/api/part-1b/evaluation` *(FR-030 to FR-032)*

200:

```json
{
  "source": "Part-1B/evidence/eval-results.json",
  "report": { "...": "file content, unchanged" },
  "cases": [ { "id": 3, "type": "normal", "input": "...", "expected_vuln": "Cross-Site Scripting (XSS)" } ],
  "dataset_source": "Part-1B/evals/dataset.json",
  "scoring": { "method": "passed_cases / completed_cases × 100; PASS only if all cases completed and score ≥ threshold" }
}
```

404 `report_unavailable` if the file is missing or not valid JSON. Read-only: no model call, no
file write.

## GET `/api/part-1b/evaluation/history` *(FR-033)*

200:

```json
{
  "caveat": "Dataset inputs, prompt and evaluator aliases changed between runs; scores are not directly comparable.",
  "runs": [ { "file": "Part-1B/evidence/eval-results-run-1-66.7pct.json", "timestamp_utc": "...",
              "total_cases": 15, "completed_cases": 15, "passed_cases": 10, "aggregate_score": 66.67,
              "status": "FAIL", "failed_case_ids": [6, 7, 9, 12, 13], "is_current": false } ]
}
```

Sorted ascending by `timestamp_utc`; includes the current report with `is_current: true`.
Unreadable files are listed with `status: "UNREADABLE"` rather than dropped.

---

## GET `/api/evidence` *(FR-040)*

200: `{ "groups": [ { "group": "historical", "title": "...", "items": [EvidenceItem] } ] }`
— only files that exist.

## GET `/api/evidence/{id}` *(FR-041)*

200: `{ "id", "label", "path", "size_bytes", "sha256", "content" }`.
404 `not_found` for any id not in the allow-list or whose file no longer exists. Path-like ids
(`..`, `/`, `\`, `%2e`) never resolve.

---

## Static routes

- `GET /` → `static/index.html`
- `GET /static/...` → CSS, JavaScript, icons
- `GET /api/openapi.json` → generated OpenAPI document. `/docs` and `/redoc` are disabled.
