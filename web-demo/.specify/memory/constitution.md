# Assignment 1 Web Demonstration Portal Constitution

Scope: this constitution governs only the `web-demo/` presentation layer. Part 1A
(`Part-1A/`) and Part 1B (`Part-1B/`) remain governed by their own Spec Kit artifacts and
harnesses. Nothing in this project may be used to change or reinterpret them.

## Core Principles

### I. Wrap, Never Rewrite

- The portal MUST call the existing Part 1A `RateLimiter` (`Part-1A/src/limiter.py`) and the
  existing Part 1B reviewer and evaluator modules (`Part-1B/src/reviewer.py`,
  `Part-1B/.harness/evaluate.py`) for all application behaviour.
- The portal MUST NOT re-implement token-bucket arithmetic, tier configuration, Gemini prompting,
  response-schema validation or evaluation scoring. Display-only reads of existing objects are
  permitted.
- The portal MUST NOT modify any file under `Part-1A/` or `Part-1B/`. Any defect found in those
  projects is reported and fixed through their own SDD artifacts and harnesses.

Rationale: the assessed engineering work is Part 1A and Part 1B; the portal is a presentation
layer and must not become a second, unvalidated implementation.

### II. Evidence Integrity

- Historical evidence (source snapshots, datasets, saved evaluation reports, harness logs,
  Spec Kit artifacts) MUST be served read-only, exactly as stored.
- The portal MUST NOT run `Part-1B/.harness/evaluate.py` or any operation that overwrites a saved
  report.
- Recorded failures (for example Part 1B cases 3 and 8 in the saved final report) MUST be shown,
  not hidden or reworded as passes.
- Claims MUST match the implementation: Part 1B Layer 3 is deterministic category/alias matching,
  not an LLM judge; a saved score is the result of one recorded run, not a general accuracy figure.
- The portal and its coding agent MUST NOT author harness-log entries, reflection answers or human
  ACCEPT/REJECT decisions.

Rationale: evaluators assess honesty of evidence; a presentation layer that embellishes it
undermines the assignment.

### III. Secret Confinement

- `GEMINI_API_KEY` MUST be read only by the backend process from the environment.
- The key MUST NOT appear in any HTTP response, HTML, JavaScript, log line, error message,
  exception text returned to the client, screenshot-facing UI or committed file.
- Configuration status MUST be exposed only as a boolean (configured / not configured).

Rationale: credential leakage is the highest-impact failure available to this project.

### IV. Untrusted Input and Output

- Source code submitted for review is untrusted data. It MUST NOT be executed, evaluated,
  imported or written to disk by the portal.
- All API inputs MUST be validated (type, length, allowed values) before reaching Part 1A or
  Part 1B code; invalid input MUST receive a 4xx response with a safe message.
- Model-generated text and evidence MUST be rendered as text (never as HTML) in the browser.
  The UI MUST NOT use `innerHTML` or equivalent sinks with server data.
- Responses MUST carry a restrictive Content-Security-Policy that forbids inline and third-party
  scripts.
- Internal stack traces MUST NOT be returned to the browser.

Rationale: a security code reviewer that is itself injectable would contradict its purpose.

### V. Real Behaviour, Honest Failures

- Part 1A outcomes (accept, HTTP 429, `Retry-After`) MUST come from real HTTP responses produced
  by the backend; the browser MUST NOT simulate or predict them.
- Part 1B findings MUST come from a live Gemini call through the existing reviewer; no mock,
  cached or keyword-generated findings may be presented as model output.
- Failures MUST be classified and shown distinctly: invalid input, missing configuration,
  quota/rate limit, upstream service error, network/timeout, and invalid model output. None of
  these may be presented as "no vulnerabilities found".

Rationale: the purpose of the demonstration is to show real behaviour, including failure modes.

### VI. Local-First Simplicity

- Stack: Python FastAPI backend, static HTML, CSS and vanilla JavaScript. No frontend build step,
  database, authentication, Docker, cloud deployment or additional AI provider.
- The server MUST bind to `127.0.0.1` by default and start on Windows with one documented command.
- The page MUST work offline apart from the Gemini call: no CDN or third-party runtime assets.
- New dependencies MUST be justified in the plan and pinned to exact versions.

Rationale: evaluators must be able to run the portal on a fresh Windows machine in minutes.

### VII. Specification-Derived Verification

- Every functional requirement MUST map to at least one automated test or, where a live external
  call is required, a documented manual verification step with recorded output.
- API tests MUST exercise the real Part 1A limiter. Gemini MAY be replaced by a test double only
  at the network boundary in automated tests; live inference MUST be verified separately.
- The `web-demo` harness (Ruff, Bandit, Pytest) MUST pass before acceptance. Tests, assertions and
  checks MUST NOT be weakened, skipped or deleted to obtain a pass.

Rationale: the portal is built the same way the assignment asks the student to build software.

## Technology and Security Constraints

- Runtime: Python 3.13; FastAPI and Uvicorn; dependencies pinned in `web-demo/requirements.txt`.
- Inputs: client ID 1-64 characters from `[A-Za-z0-9_.-]`; tier one of `free`, `standard`,
  `premium`; source code 1-20,000 characters; request bodies above 64 KB rejected.
- Browser support: current Chrome and Edge; layout usable from 360 px width upward with no
  horizontal page scroll.
- Accessibility: keyboard-operable controls, visible focus, WCAG AA text contrast, status changes
  announced through ARIA live regions.
- Performance (local): first page render under 1 second; non-Gemini API responses under 200 ms.

## Development Workflow and Quality Gates

- Work follows Spec Kit: constitution → specify → clarify → plan → tasks → analyze → implement.
- Work happens on a feature branch; nothing merges to `main` without the repository owner's review.
- Gates before acceptance: Ruff (zero findings), Bandit (zero medium or high findings), Pytest
  (all tests pass), plus the documented manual live-Gemini check.
- Harness output is saved as evidence; the human owner records the final ACCEPT/REJECT decision.

## Governance

- This constitution supersedes other practices for `web-demo/`. Plans and tasks MUST include a
  constitution check; any violation MUST be justified in the plan's Complexity Tracking table or
  removed.
- Amendments require a written change, a semantic version bump and an updated Last Amended date.
  MAJOR: principle removal or redefinition; MINOR: new principle or materially expanded guidance;
  PATCH: clarification or wording.
- Compliance is reviewed at the analyze step and again before merge.

**Version**: 1.0.0 | **Ratified**: 2026-11-06 | **Last Amended**: 2026-11-06
