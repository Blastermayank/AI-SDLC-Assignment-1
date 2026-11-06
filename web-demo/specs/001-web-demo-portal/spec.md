# Feature Specification: Assignment 1 Web Demonstration Portal

**Feature Branch**: `001-web-demo-portal`

**Created**: 2026-11-06

**Status**: Draft

**Revised**: 2026-11-07 (`/speckit-analyze` remediation: FR-004, FR-013, SC-004, server-restart
edge case, "Gemini not configured" terminology)

**Input**: User description: "Build a professional, locally runnable web demonstration portal for
BITS Pilani AI-Augmented SDLC Assignment 1 that explains the assignment, lets an evaluator
interactively exercise the existing Part 1A tiered rate limiter and the existing Part 1B
Gemini-powered security code reviewer through their real backends, presents the saved Part 1B
evaluation results honestly, and links to the engineering evidence. The existing Python
implementations, harnesses and historical evidence must be preserved and must not be weakened,
duplicated or misrepresented." (Condensed from the project handover dated 2026-11-06, sections
7-17.)

## Clarifications

### Session 2026-11-06

- Q: After a live Gemini analysis, should the page also show the harness's Layer 1 (schema) and
  Layer 2 (invariant) checks run on that response? → A: Yes. Layer 1 and Layer 2 results are
  computed by the existing Part 1B evaluation harness code and shown with the result; Layer 3 is
  shown as "not applicable: requires ground truth".
- Q: Should the Evaluation Dashboard also show the earlier saved Gemini runs as development
  history? → A: Yes, with a caveat that dataset, prompt and evaluator versions changed between
  runs, so their scores are not directly comparable.
- Q: Should the portal only display saved Part 1A harness results, or also run the harness live
  from the browser? → A: Saved results only. The portal never executes the harness or any shell
  command.
- Q: (Part 1B, recorded here for its impact on the portal) Should a blank-input "missing mandatory
  information" case be added to the Part 1B dataset? → A: Yes, as case 16 through a separate
  Part 1B specification revision and a new preserved evaluation run. Portal impact: the dashboard
  MUST NOT assume a fixed number of cases or a specific report; it displays whichever report is
  current and lists all preserved earlier reports.

## User Scenarios & Testing *(mandatory)*

Primary actor: an **evaluator** (course examiner or teaching assistant) running the portal on a
local Windows machine. Secondary actor: the **student**, who uses the portal to record a short,
silent demonstration video.

### User Story 1 - Demonstrate tiered rate limiting live (Priority: P1)

The evaluator opens the Part 1A section, enters a client ID, chooses a subscription tier and sends
requests one at a time. Each request is decided by the real rate limiter. The evaluator sees
whether each request was accepted or rejected, the HTTP status, and on rejection the retry delay
the server advertised. A running history shows every request. The tier table shows each tier's
capacity and refill rate, and a short explanation describes how tokens are consumed and refilled.

**Why this priority**: Part 1A is deterministic, has no external dependency and is the clearest
demonstration of specification-to-behaviour traceability. It is the minimum viable portal.

**Independent Test**: With only this story built, send six requests for a new Free-tier client
ID and observe five acceptances followed by an HTTP 429 rejection carrying a retry delay.

**Acceptance Scenarios**:

1. **Given** a client ID that has made no requests, **When** the evaluator sends 5 requests on
   the Free tier, **Then** all 5 are shown as accepted with HTTP status 200.
2. **Given** that client has used its 5 Free-tier tokens, **When** the evaluator sends a 6th
   request immediately, **Then** it is shown as rejected with HTTP status 429 and the retry delay
   in whole seconds taken from the server's `Retry-After` header.
3. **Given** client A is exhausted, **When** the evaluator sends a request as client B,
   **Then** client B's request is accepted (limits are isolated per client ID).
4. **Given** a client ID first used on the Free tier, **When** the evaluator selects a different
   tier for the same client ID, **Then** the portal states that the client remains on the tier
   it was first registered with and shows that tier's capacity.
5. **Given** any request history, **When** the evaluator resets the demonstration,
   **Then** all client buckets and the history are cleared and the tier configuration is
   unchanged.
6. **Given** an invalid client ID (empty, too long or containing disallowed characters) or an
   unknown tier, **When** the evaluator submits, **Then** the request is refused with a clear
   validation message and no rate-limit state changes.

---

### User Story 2 - Review source code with the live Gemini model (Priority: P2)

The evaluator opens the Part 1B section, pastes a source-code snippet and requests an analysis.
While the model works, a loading state is shown. The result lists each finding's vulnerability,
severity, description, evidence excerpt and remediation, and the raw JSON response can be
expanded. The page states that Gemini produced the result, that results can vary between
requests, that findings are review suggestions rather than proof of security, and that the
submitted code is never executed.

**Why this priority**: Live non-deterministic inference is the defining feature of Part 1B and
must be shown working end to end, but it depends on an external service, so it ranks after P1.

**Independent Test**: Submit `query = f'SELECT * FROM users WHERE id = {user_id}'` and observe a
rendered result produced by a live model call, with its raw JSON available.

**Acceptance Scenarios**:

1. **Given** the model service is configured and reachable, **When** the evaluator submits a
   vulnerable snippet, **Then** the portal displays the model's findings with all five fields
   per finding, the severity shown as High, Medium or Low, and the model name.
2. **Given** a snippet for which the model reports no issues, **When** the result arrives,
   **Then** the portal states "analysis completed, no findings reported" and does not imply
   that the code is proven secure.
3. **Given** the submission is empty or whitespace only, **When** the evaluator submits,
   **Then** the portal refuses it with a validation message and makes no model call.
4. **Given** the API credential is not configured, **When** the evaluator submits,
   **Then** the portal shows a "Gemini not configured" message and no findings.
5. **Given** the model service returns a quota/rate-limit error, a service error, times out, or
   returns output that fails the reviewer's validation, **When** the result is shown, **Then**
   each case is labelled with its own distinct error category and is never shown as an empty
   successful analysis.
6. **Given** a finding whose text contains HTML or script markup, **When** it is displayed,
   **Then** the markup is shown literally and nothing is executed or rendered as HTML.
7. **Given** an analysis is in progress, **When** the evaluator tries to submit again,
   **Then** the second submission is prevented until the first completes.
8. **Given** a completed live analysis, **When** the result is shown, **Then** the portal also
   shows the Layer 1 (schema) and Layer 2 (invariant) outcomes computed by the existing Part 1B
   evaluation harness code for that response, including any violated rule, and shows Layer 3 as
   "not applicable: requires ground truth".

---

### User Story 3 - Inspect the saved Part 1B evaluation (Priority: P3)

The evaluator opens the Evaluation Dashboard and sees the saved final evaluation report: model,
total, completed and passed cases, aggregate score, declared threshold, final status, and a
case-by-case table showing Layer 1, Layer 2 and Layer 3 outcomes with the input, expected
category, model output and failure explanation for each case. The dashboard states that this is
the result of one recorded run, explains how the score is calculated, and makes no live model
calls.

**Why this priority**: The evaluation evidence is assessed directly, but it is static data, so it
is lower risk than the live demonstrations.

**Independent Test**: Load the dashboard with the network to the model service blocked and
confirm every figure matches the saved report file.

**Acceptance Scenarios**:

1. **Given** the current saved report (reference fixture: the report saved at
   2026-11-06T06:19:02Z), **When** the dashboard loads, **Then** it shows model
   `gemini-3.5-flash-lite`, 15 total cases, 15 completed, 13 passed, aggregate score 86.7%,
   threshold 80%, and status PASS, each value identical to the file.
2. **Given** that reference report, **When** the case table is displayed, **Then** cases 3 and 8
   are marked as failed at Layer 3 with the recorded explanation, and all other cases as passed.
3. **Given** the dashboard is open, **When** any interaction occurs, **Then** no model call is
   made and no report file is modified.
4. **Given** the preserved earlier reports, **When** the evaluator opens the run history,
   **Then** every preserved run is listed in time order with its timestamp, completed and passed
   counts, score, status and failed case IDs, under a visible caveat that dataset, prompt and
   evaluator versions changed between runs.
5. **Given** a report with a different number of cases or an INCOMPLETE status, **When** it is
   the current report, **Then** the dashboard displays it accurately without assuming 15 cases,
   and shows INCOMPLETE distinctly from FAIL.

---

### User Story 4 - Understand the assignment and its methodology (Priority: P4)

The evaluator lands on an overview that explains the assignment objective, what
specification-driven development means here, why one deterministic and one non-deterministic
application were chosen, how deterministic and non-deterministic validation differ, and the
role of the automated harnesses. A methodology section walks through the workflow from problem
statement to human review, separately for Part 1A and Part 1B, including feedback, repair and
revalidation. The Part 1A section also shows the most recent saved harness results.

**Why this priority**: Explanatory content gives context but delivers no behaviour on its own.

**Independent Test**: A reader unfamiliar with the project can answer "what are the two
applications, how is each validated, and what are their known limitations" using only the
overview and methodology pages.

**Acceptance Scenarios**:

1. **Given** the landing page, **When** the evaluator reads it, **Then** it identifies both
   applications, the Gemini model powering Part 1B, and links to every main section.
2. **Given** the methodology section, **When** the evaluator reads it, **Then** each workflow
   stage is described for Part 1A and Part 1B and no stage is claimed to have produced an
   artifact that does not exist in the repository.
3. **Given** the Part 1A harness panel, **When** it is displayed, **Then** it shows the per-gate
   result (lint, security, tests), timestamp and raw output of the most recent saved harness run,
   and offers no control that executes the harness.
4. **Given** each application section, **When** the evaluator reads it, **Then** known
   limitations are listed (Part 1A: in-memory state, no sharing across processes; Part 1B: model
   variability, dataset coverage, alias-based semantic layer, service dependency).
5. **Given** the model credential is not configured, **When** any page loads, **Then** the health
   indicator shows the portal and Part 1A as available and Part 1B as "Gemini not configured",
   without revealing any credential value.
6. **Given** a public repository URL has been configured, **When** the overview loads, **Then**
   the overview and the page footer show it as a link; **Given** none is configured, **Then**
   the footer states "Repository link not configured" instead of a broken link.

---

### User Story 5 - Browse engineering evidence (Priority: P5)

The evaluator opens the Evidence section and finds grouped links to the specifications, source
code, harness scripts, evaluation dataset, saved reports, harness logs, and initial and final
source snapshots for both parts, and can view each file's content as plain text inside the
portal. Historical evidence, the new portal's own artifacts, and current environment
verification results are labelled as separate groups.

**Why this priority**: Useful navigation, but evaluators can also browse the repository
directly.

**Independent Test**: Every listed evidence item opens and its displayed content is
byte-for-byte identical to the file in the repository.

**Acceptance Scenarios**:

1. **Given** the evidence index, **When** it is displayed, **Then** only files that exist are
   listed and each is labelled with its part and category.
2. **Given** an evidence item, **When** the evaluator opens it, **Then** its content is shown as
   plain text identical to the stored file.
3. **Given** a request for a file that is not on the evidence list (including path-traversal
   attempts), **When** it is made, **Then** it is refused and no file content is returned.

---

### Edge Cases

- A client sends requests faster than the display updates: every server response is still
  recorded once, in order.
- A rejected client waits exactly the advertised retry delay and tries again: the portal shows
  whatever the server returns (correct rounding is the responsibility of Part 1A and is being
  addressed in Part 1A's own SDD cycle).
- The portal server restarts while a page is open: server-side rate-limit state is lost; on the
  next server response the page detects the new server instance, clears its request history and
  says the server was restarted, rather than showing stale rows or an error.
- Two browser tabs use the same client ID: both share the same server-side bucket.
- Submitted code is extremely long (over 20,000 characters): refused before any model call.
- Submitted code contains prompt-injection text or markup: treated as data; output still
  rendered as text.
- The model service is slow: a loading state is shown; after 60 seconds the request ends with
  the "network or timeout" category.
- The saved report file is missing or unreadable: the dashboard shows "report unavailable"
  rather than empty or zero values.
- An evidence file listed in the index is deleted after startup: opening it shows "not found".
- The browser has JavaScript disabled: a message explains that the interactive demonstrations
  require JavaScript.

## Requirements *(mandatory)*

### Functional Requirements

**Navigation and content**

- **FR-001**: The portal MUST provide six navigable sections: Project Overview, Assignment
  Methodology, Part 1A Tiered Rate Limiter, Part 1B AI Security Code Reviewer, Evaluation
  Dashboard, and Engineering Evidence.
- **FR-002**: Every factual claim about the assignment, the applications, their harnesses or
  their results MUST be consistent with the repository contents; Part 1B Layer 3 MUST be
  described as deterministic category/alias matching, not as an LLM judge.
- **FR-003**: Each application section MUST list its problem statement, intended behaviour,
  required inputs, outputs and known limitations.
- **FR-004**: The portal MUST show the public source-repository URL as a link in the overview and
  footer when it is configured (changeable without code changes, accepted only as an
  `https://github.com/<owner>/<repo>` URL), and MUST state that it is not configured otherwise.

**Part 1A**

- **FR-010**: The portal MUST display the configured tiers (Free 5 / Standard 20 / Premium 100
  tokens capacity, refilling at 5 / 20 / 100 tokens per minute) as read from the Part 1A
  implementation, not from a separate copy.
- **FR-011**: The evaluator MUST be able to send a single request for a chosen client ID and tier;
  the accept/reject decision MUST be made by the existing Part 1A rate limiter.
- **FR-012**: A rejected request MUST be delivered to the browser as an actual HTTP 429 response
  with the `Retry-After` header produced by Part 1A, and the portal MUST display both.
- **FR-013**: The portal MUST keep a visible request history (time, client ID, tier, outcome,
  HTTP status, retry delay) for the current page session, newest first, and MUST clear it
  automatically when a response shows that the server instance has changed (restart).
- **FR-014**: The portal MUST show, after each request, the tier the client is actually registered
  on and the tokens remaining as reported by the limiter, and MUST warn when the selected tier
  differs from the registered tier.
- **FR-015**: The evaluator MUST be able to reset the demonstration state (all clients), which
  clears buckets and history without changing tier configuration or limiter logic.
- **FR-016**: Client IDs MUST be 1-64 characters from letters, digits, `_`, `.` and `-`; tiers
  MUST be one of free, standard, premium; invalid input MUST be rejected with a validation
  message before reaching the limiter.
- **FR-017**: The Part 1A section MUST present the most recent saved harness results per gate
  (lint, security, tests) with timestamp and raw output, or state that none are saved. The portal
  MUST NOT execute the harness or any other shell command.

**Part 1B**

- **FR-020**: The evaluator MUST be able to submit source code (1-20,000 characters) for
  analysis; the analysis MUST be performed by the existing Part 1B reviewer using a live call to
  the configured Gemini model.
- **FR-021**: The portal MUST display for each finding: vulnerability, severity, description,
  evidence and remediation, and MUST provide the complete raw JSON response.
- **FR-022**: The portal MUST display the model name and the time taken for each analysis.
- **FR-023**: The portal MUST distinguish and label these outcomes: completed with findings,
  completed with no findings, invalid input, Gemini not configured, quota or rate limit, service
  error, network or timeout, and invalid model output.
- **FR-024**: Submitted code MUST NOT be executed, evaluated, imported or stored by the portal.
- **FR-025**: All model-generated text MUST be displayed as plain text.
- **FR-026**: Only one analysis MAY be in progress at a time; further submissions MUST be
  prevented or refused with a "busy" message until it completes.
- **FR-027**: Each completed live analysis MUST show the Layer 1 (schema) and Layer 2
  (invariant) outcomes computed by the existing Part 1B evaluation harness code, listing any
  violated rule, and MUST show Layer 3 as "not applicable: requires ground truth".
- **FR-028**: An analysis that has not completed within 60 seconds MUST end with the
  "network or timeout" category.

**Evaluation dashboard**

- **FR-030**: The dashboard MUST read the current saved evaluation report and the evaluation
  dataset read-only and display model, threshold, total, completed and passed cases, aggregate
  score, final status (PASS, FAIL or INCOMPLETE), and per-case Layer 1/2/3 outcomes with input,
  expected category, model output and failure explanation, for any number of cases.
- **FR-031**: The dashboard MUST state that the figures are from one recorded run and explain the
  scoring method (passed cases divided by completed cases, PASS only when all cases complete and
  the score is at least the threshold).
- **FR-032**: The dashboard MUST NOT trigger model calls or modify any saved report.
- **FR-033**: The dashboard MUST list every preserved earlier evaluation report in time order
  (timestamp, completed and passed counts, score, status, failed case IDs) under a caveat that
  dataset, prompt and evaluator versions changed between runs.

**Evidence**

- **FR-040**: The evidence section MUST list only existing files from a fixed allow-list,
  grouped as historical evidence, portal artifacts, and current verification results.
- **FR-041**: Opening an evidence item MUST show its exact stored content as plain text; requests
  for files outside the allow-list MUST be refused.

**Security and reliability**

- **FR-050**: The model API credential MUST never be sent to the browser, included in any
  response, or written to logs or files; configuration status MAY be shown only as configured /
  not configured.
- **FR-051**: Error responses MUST contain a safe category and message and MUST NOT contain stack
  traces or internal file paths.
- **FR-052**: The portal MUST be reachable only from the local machine by default.
- **FR-053**: The portal MUST start with a single documented command on Windows.
- **FR-054**: A health indicator MUST show whether the portal backend, the Part 1A limiter and the
  Part 1B model configuration are available.
- **FR-055**: Server logs MUST record only request method, path, status and duration; they MUST
  NOT record request bodies, submitted code, model output or credentials.

### Key Entities

- **Tier**: name, bucket capacity, refill rate per minute; defined by Part 1A.
- **Rate-limit outcome**: client ID, requested tier, registered tier, accepted or rejected, HTTP
  status, retry delay (seconds, on rejection), tokens remaining, timestamp.
- **Review submission**: source code text (untrusted, never executed).
- **Review result**: status, list of findings, model name, elapsed time, raw response, error
  category (if any).
- **Finding**: vulnerability, severity (High, Medium, Low), description, evidence, remediation.
- **Evaluation report**: timestamp, model, threshold, total/completed/passed cases, aggregate
  score, status, service error, list of case results.
- **Case result**: case ID, type, input, expected category, Layer 1/2/3 outcomes, pass, error
  explanation, model output.
- **Evidence item**: label, part (1A, 1B, portal), category, repository path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An evaluator new to the project reaches a live Part 1A rejection, with its retry
  delay shown, within 60 seconds of opening the portal.
- **SC-002**: For a new Free-tier client, requests 1-5 are accepted and request 6 is rejected with
  a retry delay of at least 1 second, in 100% of repeated trials.
- **SC-003**: 100% of request outcomes shown in the portal match the status code received from
  the server; no outcome is produced without a server response.
- **SC-004**: In the recorded live verification of at least 10 valid code submissions made while
  the model service is available, every submission ends within 60 seconds and at least 9 of 10
  end in a displayed result (findings or "no findings") rather than an error.
- **SC-005**: Zero occurrences of the API credential are found in any page asset, response body,
  response header or log captured during the test suite and manual verification.
- **SC-006**: Every figure on the Evaluation Dashboard matches the saved report file exactly
  (verified automatically).
- **SC-007**: Markup in model output or submitted code is displayed literally in 100% of tested
  injection cases.
- **SC-008**: On a fresh Windows machine with Python installed, a person following the
  documentation has the portal running within 10 minutes using one start command.
- **SC-009**: Every section is usable at 360 px width without horizontal scrolling, and every
  interactive control can be operated with the keyboard alone.

## Assumptions

- Single local user per running portal; no accounts, authentication or multi-user isolation.
- Rate-limit state lives only for the lifetime of the portal process; this mirrors Part 1A's
  documented in-memory limitation.
- A client's tier is fixed by its first request; this is existing Part 1A behaviour and is
  displayed, not changed.
- The `Retry-After` rounding defect found during the 2026-11-06 audit is fixed in Part 1A through
  Part 1A's own SDD cycle; the portal displays whatever Part 1A returns.
- Unknown tiers fall back to Free inside Part 1A; the portal rejects unknown tiers before they
  reach Part 1A, so this fallback is not exercised through the portal.
- The portal never runs the full 15-case evaluation; that remains a command-line operation that
  preserves earlier reports (manual live evaluation from the browser is out of scope).
- The model service, credential and network are provided by the operator; their absence is shown
  as a classified error.
- The public GitHub repository URL will be supplied by the owner before submission and entered
  in the portal's configuration file (FR-004).
- Demonstration video recording uses a desktop browser (current Chrome or Edge).
