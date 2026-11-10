# web-demo harness: Ruff (lint), Bandit (SAST), Pytest API/contract tests and Pytest browser
# tests (Playwright driving the installed Microsoft Edge). Research R12, task T056.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\.harness\run.ps1
#
# Every run is saved, unedited, under
#   evidence/harness-results/<UTC yyyyMMdd-HHmmss>/
# as one transcript per gate plus summary.json (format: contracts/consumed-files.md).
# The result is PASS only if every gate exits with code 0.
# Requires the development packages: .venv\Scripts\python.exe -m pip install -r requirements-dev.txt

$script:failedChecks = @()
$script:gateResults = @()

$projectDir = Split-Path -Parent $PSScriptRoot

# Prefer the project's own virtual environment when no environment is active.
$venvScripts = Join-Path $projectDir '.venv\Scripts'
if (-not $env:VIRTUAL_ENV -and (Test-Path (Join-Path $venvScripts 'python.exe'))) {
    $env:PATH = "$venvScripts;$env:PATH"
}

# Decode tool output as UTF-8 and ask the Python tools to emit UTF-8.
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }
$env:PYTHONIOENCODING = 'utf-8'
# Keep the read-only Part 1A / Part 1B folders free of __pycache__ while tests import them.
$env:PYTHONDONTWRITEBYTECODE = '1'

$startUtc = (Get-Date).ToUniversalTime()
$runId = $startUtc.ToString('yyyyMMdd-HHmmss')
$runDir = Join-Path $projectDir "evidence\harness-results\$runId"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Get-ToolVersion {
    param([string]$Command)

    try {
        $out = @(& cmd.exe /d /c "$Command 2>&1")
        if ($out.Count -gt 0 -and ([string]$out[0]) -match '(\d+\.\d+(\.\d+)*)') {
            return $Matches[1]
        }
    }
    catch { }

    return 'unavailable'
}

function Invoke-Check {
    param(
        [string]$Name,
        [string]$Command,
        [string]$Transcript
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan

    # Reset the native exit code before each check.
    $global:LASTEXITCODE = 0
    $output = @()

    try {
        # cmd.exe merges stderr into stdout so the transcript keeps the original line order.
        $output = @(& cmd.exe /d /c "$Command 2>&1")
        $exitCode = $LASTEXITCODE

        if ($null -eq $exitCode) {
            $exitCode = 0
        }
    }
    catch {
        $output += "Execution error: $_"
        $exitCode = 1
    }

    foreach ($line in $output) {
        Write-Host $line
    }
    [System.IO.File]::WriteAllLines((Join-Path $runDir $Transcript), [string[]]$output, $utf8NoBom)

    if ($exitCode -ne 0) {
        Write-Host "$Name FAILED (exit code: $exitCode)" -ForegroundColor Red
        $script:failedChecks += $Name
        $result = 'FAIL'
    }
    else {
        Write-Host "$Name PASSED" -ForegroundColor Green
        $result = 'PASS'
    }

    $script:gateResults += [ordered]@{
        name       = $Name
        command    = $Command
        exit_code  = $exitCode
        result     = $result
        transcript = $Transcript
    }
}

# Run every gate from the web-demo directory.
Push-Location $projectDir

try {
    $pythonVersion = Get-ToolVersion 'python --version'
    $tools = [ordered]@{
        ruff       = Get-ToolVersion 'ruff --version'
        bandit     = Get-ToolVersion 'bandit --version'
        pytest     = Get-ToolVersion 'python -m pytest --version'
        playwright = Get-ToolVersion 'python -m playwright --version'
    }

    Invoke-Check -Name 'SYNTAX & LINT GUARD (RUFF)' -Command 'ruff check app tests' -Transcript '01-ruff.txt'

    Invoke-Check -Name 'SECURITY / SAST GUARD (BANDIT)' -Command 'bandit -r app -ll -c pyproject.toml' -Transcript '02-bandit.txt'

    Invoke-Check -Name 'API & CONTRACT TESTS (PYTEST)' -Command 'python -m pytest -m "not e2e" -v' -Transcript '03-pytest-api.txt'

    Invoke-Check -Name 'BROWSER E2E TESTS (PLAYWRIGHT)' -Command 'python -m pytest -m e2e -v' -Transcript '04-pytest-e2e.txt'
}
finally {
    Pop-Location
}

$overall = 'PASS'
if ($script:failedChecks.Count -gt 0) {
    $overall = 'FAIL'
}

$summary = [ordered]@{
    harness       = 'web-demo'
    timestamp_utc = $startUtc.ToString('yyyy-MM-ddTHH:mm:ssZ')
    python        = $pythonVersion
    tools         = $tools
    gates         = $script:gateResults
    result        = $overall
}
[System.IO.File]::WriteAllText((Join-Path $runDir 'summary.json'), ($summary | ConvertTo-Json -Depth 5), $utf8NoBom)

Write-Host "`n========== HARNESS SUMMARY =========="

if ($script:failedChecks.Count -gt 0) {
    Write-Host 'FAILED CHECKS:' -ForegroundColor Red

    foreach ($check in $script:failedChecks) {
        Write-Host " - $check" -ForegroundColor Red
    }

    Write-Host 'HARNESS RESULT: FAIL' -ForegroundColor Red
    Write-Host "Results saved to: $runDir"
    exit 1
}

Write-Host 'All automated checks passed.' -ForegroundColor Green
Write-Host 'HARNESS RESULT: PASS' -ForegroundColor Green
Write-Host "Results saved to: $runDir"
exit 0
