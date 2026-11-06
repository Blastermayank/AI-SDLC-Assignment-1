# Data Model: Assignment 1 Web Demonstration Portal

**Feature**: `001-web-demo-portal` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

The portal owns no persistent data. Entities are either read from Part 1A/1B (source of truth
noted per entity), held in process memory, or exchanged over the HTTP API (see
[contracts/http-api.md](contracts/http-api.md)).

## Tier *(source: `Part-1A/src/limiter.py` → `TIERS`, read-only)*

| Field | Type | Rule |
|---|---|---|
| `name` | string | One of `free`, `standard`, `premium` (keys of `TIERS`) |
| `capacity` | integer | `TIERS[name]["capacity"]` |
| `refill_per_second` | number | `TIERS[name]["refill_rate"]` |
| `refill_per_minute` | number | `refill_per_second × 60` (display conversion only) |

## RateLimitRequest *(API input)*

| Field | Type | Validation (FR-016) |
|---|---|---|
| `client_id` | string | 1-64 chars, regex `^[A-Za-z0-9_.-]{1,64}$` |
| `tier` | string | Exactly one of the `Tier.name` values |

Invalid input → 422 `invalid_input`; the limiter is not called and no bucket is created.

## RateLimitOutcome *(API output; one per request)*

| Field | Type | Source |
|---|---|---|
| `accepted` | boolean | `check_request` returned `True` (accepted) or raised (rejected) |
| `status_code` | integer | 200, or the `HTTPException.status_code` raised by Part 1A (429) |
| `retry_after_seconds` | integer or null | Parsed from Part 1A's `Retry-After` header; null when accepted |
| `detail` | string or null | `HTTPException.detail` on rejection |
| `client_id` | string | Echo of validated input |
| `requested_tier` | string | Echo of validated input |
| `registered_tier` | string | Tier whose `capacity` equals the client bucket's `capacity` |
| `tier_mismatch` | boolean | `requested_tier != registered_tier` |
| `tokens_remaining` | number | Bucket `tokens` after the call, rounded to 3 decimals (display only) |
| `capacity` | integer | Bucket `capacity` |
| `timestamp_utc` | string | ISO 8601, server time of the decision |

The HTTP response's own status code and `Retry-After` header carry the same values as
`status_code` and `retry_after_seconds` (the header string is passed through unchanged).

### Client bucket lifecycle *(owned by Part 1A; observed, not modified)*

```text
(absent) --first request (tier T)--> ACTIVE[T] --tokens < 1 on request--> EXHAUSTED[T]
EXHAUSTED[T] --time passes, refill ≥ 1 token--> ACTIVE[T]
any state --portal reset (new RateLimiter instance)--> (absent)
```

The tier `T` is fixed at the first request; later requests with another tier still use `T`
(surfaced as `tier_mismatch`).

## RequestHistoryEntry *(browser memory only, current page session)*

`RateLimitOutcome` fields shown in a table, newest first. Cleared by reset or page reload.

## ReviewSubmission *(API input)*

| Field | Type | Validation (FR-020, FR-024) |
|---|---|---|
| `code` | string | 1-20,000 characters and not whitespace-only. Never executed, imported, evaluated or written to disk |

## ReviewResult *(API output on success)*

| Field | Type | Source |
|---|---|---|
| `model` | string | `part1b_evaluate.MODEL` |
| `elapsed_ms` | integer | Wall time of the reviewer call |
| `result` | object | Parsed JSON returned by `analyze_code` (status + findings) |
| `raw` | string | Exact JSON string returned by `analyze_code` |
| `live_checks.layer1` | `{passed: bool, errors: [string]}` | jsonschema `validate` with `part1b_evaluate.RESPONSE_SCHEMA` |
| `live_checks.layer2` | `{passed: bool, errors: [string]}` | `part1b_evaluate.invariant_check(result, code)` |
| `live_checks.layer3` | `{applicable: false, reason: string}` | Fixed: requires ground truth |

## Finding *(source: Part 1B output contract, rendered as plain text)*

`vulnerability` (string), `severity` (`High` / `Medium` / `Low`), `description` (string),
`evidence` (string, expected to be an exact excerpt of the submitted code), `remediation`
(string).

### Analysis lifecycle *(portal)*

```text
IDLE --submit (valid)--> IN_PROGRESS --reviewer returns--> COMPLETED (findings or none)
IN_PROGRESS --error--> FAILED[category]          IN_PROGRESS --60 s--> FAILED[network_timeout]
IN_PROGRESS --second submit--> refused (busy)    COMPLETED/FAILED --> IDLE
```

## ErrorEnvelope *(every non-2xx portal response except Part 1A's 429)*

| Field | Type | Rule |
|---|---|---|
| `error.category` | string | One of: `invalid_input`, `payload_too_large`, `forbidden_origin`, `not_found`, `busy`, `not_configured`, `quota`, `service_error`, `network_timeout`, `invalid_model_output`, `report_unavailable`, `internal_error` |
| `error.message` | string | Fixed, human-readable text per category; never contains input, stack traces, paths or credentials |
| `error.fields` | array of string | Only for `invalid_input`: names of invalid fields (no values) |

## EvaluationReport *(source: `Part-1B/evidence/eval-results*.json`, read-only)*

Fields as written by `Part-1B/.harness/evaluate.py`: `timestamp_utc`, `model`, `threshold`,
`total_cases`, `completed_cases`, `passed_cases`, `partial_score`, `aggregate_score` (number or
null), `status` (`PASS` / `FAIL` / `INCOMPLETE`), `service_error` (object or null), `results`
(array of CaseResult). The portal passes the file content through unchanged.

## CaseResult *(inside EvaluationReport)*

`id`, `layer1`, `layer2`, `layer3`, `pass` (booleans except `id`), `error` (string),
`model_output` (object or null), optional `service_error` / `execution_error` flags.
For the **current** report only, the portal attaches `type`, `input` and `expected_vuln` from
`Part-1B/evals/dataset.json` by `id` (research R13).

## RunSummary *(derived, history list)*

`file`, `timestamp_utc`, `total_cases`, `completed_cases`, `passed_cases`, `aggregate_score`,
`status`, `failed_case_ids` (ids where `pass` is false), `is_current` (boolean).

## HarnessRunSummary *(source: `<project>/evidence/harness-results/<run>/summary.json`)*

Format defined in [contracts/consumed-files.md](contracts/consumed-files.md): `harness`,
`timestamp_utc`, `python`, `tools`, `gates[]` (`name`, `command`, `exit_code`, `result`,
`transcript`), `result`.

## EvidenceItem *(allow-list, built in code)*

| Field | Type | Rule |
|---|---|---|
| `id` | string | Stable slug; the only key accepted by the content endpoint |
| `label` | string | Human-readable name |
| `group` | string | `historical`, `portal`, `verification` |
| `part` | string | `1A`, `1B`, `portal`, `repository` |
| `path` | string | Repository-relative path (display only) |
| `size_bytes` | integer | Present only if the file exists; non-existent items are omitted |

Content response adds `content` (UTF-8 text, BOM preserved) and `sha256` of the raw bytes.
