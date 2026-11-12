# Assignment 1 — Spec-Driven Development and Harness Engineering

This repository contains two projects demonstrating specification-driven development and automated validation:

- **Part 1A:** A deterministic tiered rate-limiter component using the Token Bucket algorithm.
- **Part 1B:** A non-deterministic AI-assisted security code review application using actual Google Gemini API inference.

Each project includes a specification, implementation, and development evidence. Part 1A includes an automated quality/security/test harness; Part 1B includes a three-layer evaluation harness. A local web portal (`web-demo/`) presents and runs both projects.

Technical documentation: [docs/architecture.md](docs/architecture.md) (how each part works) and [docs/testing-and-evidence.md](docs/testing-and-evidence.md) (every harness, every saved run, and how to verify the evidence).

## Quick start on Windows

1. Install Python 3.13 (`winget install Python.Python.3.13`) and Git, then get the repository:

   ```powershell
   git clone https://github.com/Blastermayank/AI-SDLC-Assignment-1.git Assignment-1
   cd Assignment-1
   ```

2. For Part 1B and the portal's live analysis, store a Google Gemini API key as the Windows user environment variable `GEMINI_API_KEY` (see [Configure Gemini authentication](#configure-gemini-authentication)), then open a new PowerShell window.
3. Start the web portal (it creates its own virtual environment on first run) and open `http://127.0.0.1:8000`:

   ```powershell
   cd web-demo
   powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
   ```

4. To run each part's own harness, follow the installation steps in the Part 1A and Part 1B sections below.

## Repository structure

```text
Assignment-1/
├── README.md
├── docs/                          technical documentation
├── Part-1A/                       deterministic: tiered rate limiter
│   ├── speckit.constitution.md    Spec Kit constitution
│   ├── speckit.specify.md         specification, acceptance criteria, clarifications
│   ├── change-cycles/             plan and tasks of the 2026-11-07 AC3 change cycle
│   ├── src/limiter.py             Token Bucket implementation
│   ├── tests/test_limiter.py      specification-derived tests
│   ├── .harness/run.ps1           harness: Ruff, Bandit, Pytest
│   ├── requirements.txt           pinned dependencies
│   ├── harness-log.md             harness log and human decision
│   └── evidence/
│       ├── README.md              index of the evidence
│       ├── initial-generation/    first generated implementation
│       ├── final-generation/      implementation after harness-driven repair
│       └── harness-results/       every saved harness run (transcripts + summary.json)
├── Part-1B/                       non-deterministic: Gemini security code reviewer
│   ├── speckit.constitution.md
│   ├── speckit.specify.md         specification: output schema, invariants, threshold
│   ├── change-cycles/             plan and tasks of the 2026-11-07 missing-input change cycle
│   ├── src/reviewer.py            Gemini call and response validation
│   ├── evals/dataset.json         16 evaluation cases
│   ├── .harness/evaluate.py       three-layer evaluation harness
│   ├── tests/                     unit tests for the evaluator (no network)
│   ├── requirements.txt
│   ├── harness-log.md
│   └── evidence/
│       ├── README.md              index of every evaluation run
│       ├── initial-generation/, final-generation/
│       ├── dataset-before-security-refinement.json
│       ├── eval-results.json      current report; earlier runs kept as eval-results-run-*.json
│       ├── eval-console/          console output of evaluator runs
│       └── unit-test-results/     saved unit-test runs
└── web-demo/                      local web portal presenting both parts (built with Spec Kit)
    ├── README.md
    ├── start.ps1                  one-command start
    ├── app/, static/              FastAPI backend; HTML, CSS and JavaScript frontend
    ├── tests/                     API, security and browser tests
    ├── .harness/run.ps1           portal harness
    ├── specs/001-web-demo-portal/ Spec Kit specification, plan, research, contracts, tasks
    ├── .specify/                  Spec Kit configuration and the portal constitution
    └── evidence/                  harness runs, live Gemini and quickstart validation records
```

## Prerequisites

- Windows with PowerShell.
- Python 3.13 (verified with CPython 3.13.18 on 2026-11-07). The original development on 2026-11-05/06 used Python 3.10. The pinned test tools (pytest 9.2.0) do not run on CPython 3.10.0 because of a dataclass defect in that interpreter release.
- Internet connectivity and a valid Gemini API key for Part 1B.

Part 1A and Part 1B use separate virtual environments and dependency files. Run commands from the relevant project directory.

## Web demonstration portal

The `web-demo/` folder contains a local web page that explains both projects and runs them live: send requests through the Part 1A rate limiter, submit code to the Part 1B Gemini reviewer, view the saved Part 1B evaluation results, and browse the engineering evidence. It is a presentation layer only: it loads `Part-1A/src/limiter.py` and `Part-1B/.harness/evaluate.py` unchanged and never modifies Part 1A or Part 1B.

```powershell
cd web-demo
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

The portal opens at `http://127.0.0.1:8000`. Setup, the portal's own harness, security notes and troubleshooting are in [web-demo/README.md](web-demo/README.md). It was built with GitHub Spec Kit; its specification, plan and tasks are in `web-demo/specs/001-web-demo-portal/`.

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
- **AC3:** Rejected requests include a `Retry-After` header giving the smallest whole number of seconds after which a retry is accepted (clarified 2026-11-07; see `Part-1A/speckit.specify.md`).
- **AC4:** Rate limits are isolated by client ID.

## Installation

Open PowerShell and run:

```powershell
Set-Location "<repository-path>\Part-1A"
py -3.13 -m venv .venv   # or: python3.13 -m venv .venv (if Python was installed with uv)
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

Each check reports its own result. The harness exits with code `0` only when all checks pass; otherwise it exits with a non-zero code. If `Part-1A\.venv` exists and no virtual environment is active, the harness uses it automatically.

Every run is saved, unedited, in `Part-1A/evidence/harness-results/<UTC yyyyMMdd-HHmmss>/`: one transcript per gate (`01-ruff.txt`, `02-bandit.txt`, `03-pytest.txt`) and `summary.json` with the Python and tool versions and each gate's command, exit code and result. Tool versions are pinned in `requirements.txt` so the gates behave the same on every machine.

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
import sys

sys.path.insert(0, "src")  # reviewer.py lives in Part-1B/src
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

**16-case dataset (since 2026-11-07):** no completed evaluation yet. Every attempt so far (runs 7-17 and the current report) was stopped by a Gemini service problem, almost always `503 UNAVAILABLE` ("model is currently experiencing high demand"), and is recorded as `INCOMPLETE`, not as a pass or a failure. The furthest attempts were run 7 (14 of 16 cases completed, 12 passed; partial score 85.7%, not final) and the current report of 2026-11-13 (13 of 16 completed, 11 passed; partial score 84.6%, not final). In every attempt, the only cases that failed were 3 and 8, both at the semantic layer, as in run 6. See `Part-1B/evidence/README.md` for every saved run.

---

## Evidence and development history

Both projects preserve separate initial-generation and final-generation source snapshots. Part 1B also retains the dataset before the security-focused refinements and historical evaluation reports.

Historical reports document outcomes observed during development. Since the model is non-deterministic and the dataset inputs were refined, do not treat all historical scores as directly comparable unless the dataset version for each run is known.

On 2026-11-07 each part went through a recorded change cycle (specification clarification, plan and tasks, tests first, a recorded failure, the repair, a recorded pass). The plans and tasks are in each part's `change-cycles/` folder, and every saved run is listed in `Part-1A/evidence/README.md` and `Part-1B/evidence/README.md`. [docs/testing-and-evidence.md](docs/testing-and-evidence.md) summarises all of it, with the commit for each step.

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
- The 16-case dataset has no completed evaluation yet (Gemini service errors on every attempt so far).
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
| Web portal | FastAPI, uvicorn, HTML/CSS/vanilla JavaScript; Ruff, Bandit, Pytest, Playwright (Edge) |
| Version control | Git, GitHub |
