# Constitution: SecureRateLimiter

## Core Principles
1. **Deterministic Behavior**: The rate limiter must use a strict Token Bucket algorithm.
2. **In-Memory Operations**: Storage must be handled via an in-memory adapter; no external databases allowed.
3. **Security First**: Code must pass Bandit SAST scanning with zero high-severity vulnerabilities.
4. **Code Quality**: Code must pass Ruff linting with zero errors.

## Technical Constraints
- Language: Python 3.10+
- Framework: FastAPI (using standard Starlette requests)
- Testing: Pytest (Mandatory deterministic tests must pass before acceptance)
