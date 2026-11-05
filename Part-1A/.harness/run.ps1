Write-Host "
=== SYNTAX & LINT GUARD (RUFF) ==="
ruff check src/

Write-Host "
=== SECURITY / SAST GUARD (BANDIT) ==="
bandit -r src/ -ll

Write-Host "
=== UNIT & CONTRACT TESTS (PYTEST) ==="
python -m pytest tests/ -v
