# Part 1A harness: Ruff (lint), Bandit (SAST) and Pytest (unit and contract tests).
# Gate names, commands, order and the PASS/FAIL rule are unchanged from the original harness.
# Since 2026-11-07 every run is also saved, unedited, under
#   evidence/harness-results/<UTC yyyyMMdd-HHmmss>/
# as one transcript per gate plus summary.json.

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

# Resolve the Part-1A directory from this script's location.
Push-Location $projectDir

try {
    $pythonVersion = Get-ToolVersion 'python --version'
    $tools = [ordered]@{
        ruff   = Get-ToolVersion 'ruff --version'
        bandit = Get-ToolVersion 'bandit --version'
        pytest = Get-ToolVersion 'python -m pytest --version'
    }

    Invoke-Check -Name "SYNTAX & LINT GUARD (RUFF)" -Command "ruff check src/" -Transcript "01-ruff.txt"

    Invoke-Check -Name "SECURITY / SAST GUARD (BANDIT)" -Command "bandit -r src/ -ll" -Transcript "02-bandit.txt"

    Invoke-Check -Name "UNIT & CONTRACT TESTS (PYTEST)" -Command "python -m pytest tests/ -v" -Transcript "03-pytest.txt"
}
finally {
    Pop-Location
}

$overall = 'PASS'
if ($script:failedChecks.Count -gt 0) {
    $overall = 'FAIL'
}

$summary = [ordered]@{
    harness       = 'Part-1A'
    timestamp_utc = $startUtc.ToString('yyyy-MM-ddTHH:mm:ssZ')
    python        = $pythonVersion
    tools         = $tools
    gates         = $script:gateResults
    result        = $overall
}
[System.IO.File]::WriteAllText((Join-Path $runDir 'summary.json'), ($summary | ConvertTo-Json -Depth 5), $utf8NoBom)

Write-Host "`n========== HARNESS SUMMARY =========="

if ($script:failedChecks.Count -gt 0) {
    Write-Host "FAILED CHECKS:" -ForegroundColor Red

    foreach ($check in $script:failedChecks) {
        Write-Host " - $check" -ForegroundColor Red
    }

    Write-Host "HARNESS RESULT: FAIL" -ForegroundColor Red
    Write-Host "Results saved to: $runDir"
    exit 1
}

Write-Host "All automated checks passed." -ForegroundColor Green
Write-Host "HARNESS RESULT: PASS" -ForegroundColor Green
Write-Host "Results saved to: $runDir"
exit 0
