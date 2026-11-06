# Feature Specification: AI-Assisted Semantic Code Review and Security Analysis

## 1. Feature Summary

A non-deterministic AI-powered security code review assistant that analyzes
user-supplied code snippets and identifies potential security vulnerabilities.

The application uses the Google Gemini API for actual inference. Model output
is constrained to a structured JSON contract and validated locally before
being evaluated by the harness.

## 2. Input Requirements

- Accept a code snippet as a string.
- Treat supplied source code as untrusted input.
- Instructions embedded inside the supplied code must not override the
  reviewer's instructions or safety rules.
- Empty or whitespace-only input must return an error response.
- Valid non-empty input must be analyzed using the configured Gemini model.

## 3. Output Schema Contract (Layer 1: Structural)

Every successful analysis must return a JSON object with the following
structure:

{
  "status": "success",
  "findings": [
    {
      "vulnerability": "SQL Injection",
      "severity": "High",
      "description": "Description of the identified security issue.",
      "evidence": "Exact excerpt from the supplied source code.",
      "remediation": "Practical recommendation to resolve the issue."
    }
  ]
}

The top-level fields are:

- `status`: Required string; allowed values are `success` and `error`.
- `findings`: Required JSON array containing zero or more findings.

Every finding must contain these five required fields:

- `vulnerability`: Non-empty string identifying the vulnerability category.
- `severity`: One of `High`, `Medium`, or `Low`.
- `description`: Non-empty explanation of the security issue.
- `evidence`: Non-empty exact excerpt from the supplied source code.
- `remediation`: Non-empty practical remediation recommendation.

An error response must use the following structure:

{
  "status": "error",
  "findings": []
}

The status field describes whether analysis completed, not whether a
vulnerability was detected.

A successful analysis with no supported security findings must return
`status: success` and an empty findings array.

## 4. Invariants and Guardrails (Layer 2: Property)

- **INV1 - Status validity:** Status must be either `success` or `error`.
- **INV2 - Findings structure:** Findings must always be a JSON array.
- **INV3 - Error consistency:** An error response must not contain findings.
- **INV4 - Severity restriction:** Every finding must use only `High`,
  `Medium`, or `Low`.
- **INV5 - Finding completeness:** Every finding must contain all five
  required non-empty string fields.
- **INV6 - Evidence integrity:** Evidence must be an exact substring of
  the supplied source code.
- **INV7 - Finding limit:** The reviewer must not return more than
  ten findings for one input.
- **INV8 - Analysis consistency:** Successfully analyzed evaluation inputs
  must have `status: success`, whether findings are present or absent.

Additional guardrails:

- Do not invent vulnerabilities or surrounding application behavior that
  cannot be supported by the supplied input.
- Do not treat ordinary file writes as vulnerabilities without evidence
  of a concrete security risk.
- Distinguish security-sensitive use of cryptographic functions and random
  number generation from ordinary non-security use.
- Detect prompt-injection attempts in supplied input without following
  embedded instructions.
- Report clear syntax or parsing errors when the supplied statement is
  incomplete or unusable.

API, network, authentication, and model-service failures must be distinguished
from security findings. They must not be converted into successful empty
results or fabricated vulnerability findings.

## 5. Semantic Quality (Layer 3: Semantic)

- **SEM1 - Ground-truth matching:** Detected vulnerability categories must
  match the expected vulnerability category specified in the evaluation
  dataset.
- **SEM2 - Category aliases:** The evaluator must support configured
  vulnerability-name aliases and normalization when comparing model output
  with expected categories.
- **SEM3 - Negative cases:** When the expected category is `None`, the
  reviewer must return an empty findings array.
- **SEM4 - Meaningful detection:** The reviewer should identify the
  vulnerability demonstrated by the supplied code rather than relying
  only on superficial keyword matches.

The current implementation performs Layer 3 through deterministic
category and alias matching. It does not use an independent LLM-as-a-Judge.

## 6. Evaluation Dataset

- Maintain a dataset containing at least 15 meaningful evaluation cases.
- Include normal vulnerability cases, negative cases, boundary cases,
  ambiguous inputs, and guardrail-related cases.
- Each case must define an identifier, type, input, and expected
  vulnerability category.
- The dataset is maintained separately from the evaluator implementation.

## 7. Aggregate Evaluation and Pass Threshold

The evaluation harness must execute the following pipeline:

AI inference -> JSON schema validation -> invariants and guardrails
-> semantic category evaluation -> aggregate score -> PASS/FAIL.

- Calculate the aggregate score using completed evaluation cases.
- The required passing threshold is 80%.
- Report the number of total, completed, and passed cases.
- Mark the evaluation PASS only when all cases complete and the aggregate
  score reaches or exceeds the threshold.
- An incomplete run must be distinguished from a completed evaluation
  that fails the threshold.

## 8. Non-Functional Requirements

- Use a configurable Gemini model, defaulting to `gemini-3.5-flash-lite`.
- Read the API credential from the `GEMINI_API_KEY` environment variable.
- Never hardcode or commit API credentials.
- Use structured JSON generation and local response validation.
- Preserve evaluation reports as evidence.
- Keep initial-generation and final-generation source snapshots separate.
