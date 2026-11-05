# Constitution: AI Security Code Reviewer

## Core Principles
1. **Structural Reliability**: The AI must consistently return well-formed JSON matching the exact schema contract.
2. **Deterministic Evaluation of Non-Determinism**: Output variance is allowed in the explanation, but structural invariants (severity levels, field presence) must strictly pass.
3. **Fail-Safe**: If code cannot be analyzed, the system must return a defined error schema rather than crashing.

## Evaluation Threshold
- The system must achieve an **80% or higher aggregate pass rate** across the 15-case evaluation dataset before final acceptance.
