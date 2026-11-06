# Contract: User Interface

**Feature**: `001-web-demo-portal`

Stable hooks for browser tests and the demonstration video. Visual design may change; these
identifiers and behaviours may not without updating this contract.

## Sections (hash routes, FR-001)

| Hash | Section id | Heading |
|---|---|---|
| `#overview` (default) | `section-overview` | Project Overview |
| `#methodology` | `section-methodology` | Assignment Methodology |
| `#part-1a` | `section-part-1a` | Part 1A: Tiered Rate Limiter |
| `#part-1b` | `section-part-1b` | Part 1B: AI Security Code Reviewer |
| `#evaluation` | `section-evaluation` | Evaluation Dashboard |
| `#evidence` | `section-evidence` | Engineering Evidence |

Exactly one section is visible at a time. Navigation links carry `aria-current="page"` when
active. A `<noscript>` message explains that interactive demonstrations need JavaScript.

## Global

- `#health-badge`: shows portal, Part 1A and Part 1B status ("Gemini configured" /
  "Gemini not configured"). Never shows any part of the key.
- `#theme-toggle`: switches light/dark; follows the OS preference by default.
- `#repo-link` (footer) and `#overview-repo-link`: the configured repository URL as a link, or the
  text "Repository link not configured".
- The page icon is `/static/img/icon.svg`.

## Part 1A

| Element | Behaviour |
|---|---|
| `#rl-client-id` (input) | Client ID; default `demo-client` |
| `#rl-tier` (select) | free / standard / premium |
| `#rl-send` (button) | Sends one request; disabled while the request is pending |
| `#rl-reset` (button) | Resets all buckets and clears history |
| `#rl-last-outcome` (aria-live="polite") | Last outcome: ACCEPTED/REJECTED, HTTP status, `Retry-After` |
| `#rl-tier-warning` | Visible only when `tier_mismatch` is true |
| `#rl-history` (table body) | One row per server response, newest first; cleared with a "server restarted" notice when `server_instance` changes |
| `#rl-tiers` (table) | Tier configuration from `/api/part-1a/tiers` |
| `#rl-harness` | Latest saved harness run, or "No saved harness results" |

## Part 1B

| Element | Behaviour |
|---|---|
| `#rv-code` (textarea) | Source code, `maxlength=20000`, character counter `#rv-count` |
| `#rv-analyze` (button) | Disabled while empty, while over limit, and while an analysis runs |
| `#rv-status` (aria-live="polite") | Loading / completed / error category message |
| `#rv-findings` | One card per finding: vulnerability, severity badge, description, evidence (monospace), remediation |
| `#rv-live-checks` | Layer 1, Layer 2 pass/fail with errors; Layer 3 "not applicable" |
| `#rv-raw` (`<details>`) | Raw JSON response as text |
| `#rv-samples` | Buttons that load example snippets into the textarea (no auto-submit) |

## Evaluation

| Element | Behaviour |
|---|---|
| `#ev-report-select` | Chooses the displayed report (default: current) |
| `#ev-view-latest` | Shows the latest completed (PASS or FAIL) run |
| `#ev-latest` | Visible when the current report is INCOMPLETE; names the latest completed run |
| `#ev-summary` | Model, total, completed, passed, score (1 decimal), threshold, status badge |
| `#ev-cases` (table body) | One row per case: id, type, L1, L2, L3, result; expandable detail with input, expected, model output, explanation |
| `#ev-history` | Run history table with caveat text |

## Evidence

| Element | Behaviour |
|---|---|
| `#evd-groups` | Grouped item list (historical / portal / verification) |
| `#evd-viewer` | Selected file: path, size, SHA-256 and content in `<pre>` as text |

## Rendering rule

All server-supplied strings are inserted with `textContent` (or attribute setters for
non-URL attributes). No server data is inserted as HTML anywhere.
