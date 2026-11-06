$script:failedChecks = @()

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan

    # Reset the native exit code before each check.
    $global:LASTEXITCODE = 0

    try {
        & $Command
        $exitCode = $LASTEXITCODE

        if ($null -eq $exitCode) {
            $exitCode = 0
        }
    }
    catch {
        Write-Host "Execution error: $_" -ForegroundColor Red
        $exitCode = 1
    }

    if ($exitCode -ne 0) {
        Write-Host "$Name FAILED (exit code: $exitCode)" -ForegroundColor Red
        $script:failedChecks += $Name
    }
    else {
        Write-Host "$Name PASSED" -ForegroundColor Green
    }
}

# Resolve the Part-1A directory from this script's location.
Push-Location (Split-Path -Parent $PSScriptRoot)

try {
    Invoke-Check -Name "SYNTAX & LINT GUARD (RUFF)" -Command {
        ruff check src/
    }

    Invoke-Check -Name "SECURITY / SAST GUARD (BANDIT)" -Command {
        bandit -r src/ -ll
    }

    Invoke-Check -Name "UNIT & CONTRACT TESTS (PYTEST)" -Command {
        python -m pytest tests/ -v
    }
}
finally {
    Pop-Location
}

Write-Host "`n========== HARNESS SUMMARY =========="

if ($script:failedChecks.Count -gt 0) {
    Write-Host "FAILED CHECKS:" -ForegroundColor Red

    foreach ($check in $script:failedChecks) {
        Write-Host " - $check" -ForegroundColor Red
    }

    Write-Host "HARNESS RESULT: FAIL" -ForegroundColor Red
    exit 1
}

Write-Host "All automated checks passed." -ForegroundColor Green
Write-Host "HARNESS RESULT: PASS" -ForegroundColor Green
exit 0
