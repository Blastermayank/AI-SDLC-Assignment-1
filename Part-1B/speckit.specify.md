# Feature Specification: AI Security Code Reviewer

## Feature Summary
An AI assistant that analyzes code snippets and returns structured security findings.

## Output Schema Contract (Layer 1: Structural)
Outputs must be parseable JSON matching this exact structure:
{ "status": "success|error", "findings": [ { "vulnerability": "string", "severity": "High|Medium|Low", "remediation": "string" } ] }

## Invariants & Guardrails (Layer 2: Property)
- **INV1**: severity must only be "High", "Medium", or "Low".
- **INV2**: If status is "error", indings must be an empty list.

## Semantic Quality (Layer 3: Semantic)
- **SEM1**: The identified vulnerability must logically match the known ground truth in the evaluation dataset (e.g., catching SQLi when SQLi is present).
