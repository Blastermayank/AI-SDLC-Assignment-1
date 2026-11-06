# Assignment 1 — Spec-Driven Development and Harness Engineering

This repository contains two projects demonstrating specification-driven development and automated validation:

- **Part 1A:** A deterministic tiered rate-limiter component using the Token Bucket algorithm.
- **Part 1B:** A non-deterministic AI-assisted security code review application using actual Google Gemini API inference.

Each project includes a specification, implementation, and development evidence. Part 1A includes an automated quality/security/test harness; Part 1B includes a three-layer evaluation harness.

## Repository structure

```text
Assignment-1/
├── .gitignore
├── README.md
├── Part-1A/
│   ├── .harness/run.ps1
│   ├── evidence/
│   │   ├── initial-generation/limiter_initial.py
│   │   └── final-generation/limiter_final.py
│   ├── src/limiter.py
│   ├── tests/test_limiter.py
│   ├── requirements.txt
│   ├── speckit.constitution.md
│   ├── speckit.specify.md
│   └── harness-log.md
└── Part-1B/
    ├── .harness/evaluate.py
    ├── evals/dataset.json
    ├── evidence/
    │   ├── initial-generation/
    │   ├── final-generation/
    │   ├── dataset-before-security-refinement.json
    │   └── eval-results*.json
    ├── src/reviewer.py
    ├── requirements.txt
    ├── speckit.constitution.md
    ├── speckit.specify.md
    └── harness-log.md
```

## Prerequisites

- Windows with PowerShell.
- Python 3.10 recommended. The project was developed and verified using Python 3.10.11.
- Internet connectivity and a valid Gemini API key for Part 1B.

Part 1A and Part 1B use separate virtual environments and dependency files. Run commands from the relevant project directory.

---

# Part 1A — Tiered Rate Limiter

## Overview

Part 1A implements a deterministic rate-limiting component using the Token Bucket algorithm. Each client ID has an independent in-memory token bucket.

| Tier | Bucket capacity | Refill rate |
|---|---:|---:|
| Free | 5 | 5 requests/minute |
| Standard | 20 | 20 requests/minute |
| Premium | 100 | 100 requests/minute |

The component accepts requests while tokens are available. When a client's bucket is exhausted, it raises a FastAPI `HTTPException` with HTTP status `429` and a `Retry-After` header. The implementation is a Python component; it is not, by itself, a separately deployed HTTP server or complete API service.

### Acceptance criteria

- **AC1:** Requests within the configured limit are accepted.
- **AC2:** Requests exceeding the limit are rejected with HTTP 429.
- **AC3:** Rejected requests include an appropriate `Retry-After` header.
- **AC4:** Rate limits are isolated by client ID.

## Installation

Open PowerShell and run:

```powershell
Set-Location "<repository-path>\Part-1A"
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell prevents virtual-environment activation, allow it for the current PowerShell process only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run the Part 1A harness

From the `Part-1A` directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\.harness\run.ps1"
```

The harness executes:

1. **Ruff** — lint and import-format checks.
2. **Bandit** — static application security testing.
3. **Pytest** — unit and acceptance-criteria tests.

Each check reports its own result. The harness exits with code `0` only when all checks pass; otherwise it exits with a non-zero code.

Run the tests separately, if needed:

```powershell
python -m pytest tests/ -v
```

---

# Part 1B — AI-Assisted Security Code Review

## Overview

Part 1B sends a supplied code snippet to the Google Gemini API and returns structured security findings. The application uses real model inference; its output is non-deterministic, so repeated evaluations can produce different results.

### Model and configuration

- Default model: `gemini-3.5-flash-lite`.
- Python SDK: `google-genai`.
- API credential: `GEMINI_API_KEY` environment variable.
- Optional model override: `GEMINI_MODEL` environment variable.

The reviewer uses structured JSON generation and performs local response validation. Never hardcode an API key or commit it to the repository.

## Installation

Open a separate PowerShell session and run:

```powershell
Set-Location "<repository-path>\Part-1B"
py -3.13 -m venv .venv   # or: python3.13 -m venv .venv (if Python was installed with uv)
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configure Gemini authentication

Configure `GEMINI_API_KEY` as a Windows user or process environment variable. For a persistent user-level setting, use Windows **Environment Variables** settings, then open a new PowerShell session. Do not put the key in `reviewer.py`, the README, screenshots, or Git commits.

Check whether it is configured without displaying its value:

```powershell
if ($env:GEMINI_API_KEY) {
    Write-Host "Gemini API key is configured. Value hidden."
} else {
    Write-Host "Gemini API key is missing."
}
```

The default model is `gemini-3.5-flash-lite`. To override it for the current PowerShell session:

```powershell
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
```

## Run a sample analysis

From the `Part-1B` directory, with the virtual environment active and the API key configured:

```powershell
@'
import json
from reviewer import analyze_code

sample = "query = f'SELECT * FROM users WHERE id = {user_id}'"
result = analyze_code(sample)
print(json.dumps(json.loads(result), indent=2))
'@ | python -
```

This command makes an actual Gemini API request and therefore needs network access and a valid API credential.

## Run the evaluation harness

From the `Part-1B` directory:

```powershell
python .\.harness\evaluate.py
```

The evaluator reads the dataset at `evals/dataset.json` (16 cases since 2026-11-07) and writes its report to `evidence/eval-results.json`. Before writing, it automatically archives the previous report as `evidence/eval-results-run-<N>-<score>pct.json` (or `-incomplete`), so no run overwrites an earlier result. Each report records the SHA-256 of the dataset's canonical JSON content. A full run makes one live Gemini call per case, except for the blank-input case 16, which needs no call.

Run the evaluator's unit tests (no network, no API key needed):

```powershell
python -m pytest tests -v
```

### Three-layer evaluation

The evaluation pipeline is:

**Layer 1 — Structural validation**

- Parse the model response as JSON.
- Validate the response against the JSON Schema.
- Check required fields and allowed severity values (`High`, `Medium`, `Low`).

**Layer 2 — Invariants and guardrails**

- Check consistency between response status and findings, and that the status matches the case's expected status (`success`, or `error` for the blank-input case).
- Enforce severity restrictions and the finding-count limit.
- Confirm that each evidence value is an exact excerpt from the supplied source.

**Layer 3 — Semantic evaluation**

- Compare detected vulnerability categories with the expected dataset category.
- Apply configured category aliases and normalization.
- Check negative cases where the expected value is `None`.

Layer 3 currently uses deterministic category/alias matching. It is not an independent LLM-as-a-Judge.

### Passing threshold and saved result

The configured aggregate passing threshold is **80%**.

**Latest completed evaluation** (run 6, `evidence/eval-results-run-6-86.7pct.json`, 2026-11-06, 15-case dataset):

| Metric | Saved result |
|---|---:|
| Model | `gemini-3.5-flash-lite` |
| Total cases | 15 |
| Completed cases | 15 |
| Passed cases | 13 |
| Aggregate score | 86.7% |
| Threshold | 80% |
| Status | PASS |

Cases 3 and 8 failed the semantic layer in this run. It is the result of one evaluation run on the 15-case dataset, not a general accuracy guarantee. Model outputs and scores may vary between runs.

**16-case dataset (since 2026-11-07):** no completed evaluation yet. Both runs on 2026-11-07 were stopped by Gemini `503 UNAVAILABLE` ("model is currently experiencing high demand") service errors and are recorded as `INCOMPLETE`, not as passes or failures. The first got 14 of 16 cases through, with 12 passed (partial score 85.7%, not final); the second stopped on case 1. See `Part-1B/evidence/README.md` for every saved run.

---

## Evidence and development history

Both projects preserve separate initial-generation and final-generation source snapshots. Part 1B also retains the dataset before the security-focused refinements and historical evaluation reports.

Historical reports document outcomes observed during development. Since the model is non-deterministic and the dataset inputs were refined, do not treat all historical scores as directly comparable unless the dataset version for each run is known.

## Security considerations

- Keep API credentials in environment variables; never commit them.
- Treat submitted source code as untrusted input.
- Do not follow instructions embedded in analyzed source code.
- Validate model output before consuming it.
- Treat AI-generated findings as review suggestions, not proof that code is secure or insecure.
- Review findings manually before making security decisions.

## Known limitations

### Part 1A

- Token buckets are stored in process memory and are lost when the process restarts.
- Separate application workers or replicas do not share in-memory state.
- A shared store such as Redis would be needed for coordinated rate limiting across multiple instances.

### Part 1B

- Inference depends on Gemini API availability, network connectivity, and a valid API credential.
- Model responses may vary between runs.
- The 16-case dataset cannot represent every vulnerability, language, or application context.
- The 16-case dataset has no completed evaluation yet (Gemini service errors on 2026-11-07).
- Semantic evaluation uses category aliases rather than an independent semantic judge.
- Passing the 80% threshold does not establish production-grade security-review reliability.

## Technologies

| Area | Technologies |
|---|---|
| Part 1A | Python, FastAPI `HTTPException`, Token Bucket |
| Part 1A quality and tests | Ruff, Bandit, Pytest |
| Part 1B AI integration | Google Gemini API, `google-genai` |
| Part 1B contract validation | JSON Schema, `jsonschema` |
| Part 1B evaluation | Python evaluation harness |
| Version control | Git, GitHub |
