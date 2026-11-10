# Start the web demonstration portal on this computer (FR-053, research R14).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 [-Port 8000] [-NoBrowser]
#
# What it does, in order:
#   1. finds Python 3.13 and creates web-demo\.venv on first use;
#   2. installs the pinned packages from requirements.txt (again only when that file changes);
#   3. reports whether GEMINI_API_KEY is configured - never its value;
#   4. serves the portal on http://127.0.0.1:<Port> (this computer only) until Ctrl+C,
#      opening the browser once the portal answers.

param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8000,
    [switch]$NoBrowser
)

# Native tools write progress to stderr; check exit codes explicitly instead of stopping on it.
$ErrorActionPreference = 'Continue'
$portalDir = $PSScriptRoot
$venvDir = Join-Path $portalDir '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$requirements = Join-Path $portalDir 'requirements.txt'
$marker = Join-Path $venvDir 'requirements.sha256'
$versionCheck = 'import sys;print(sys.version_info[0]*100+sys.version_info[1])'

function Write-Step([string]$Text) { Write-Host "[portal] $Text" -ForegroundColor Cyan }
function Stop-Start([string]$Text) {
    Write-Host "[portal] $Text" -ForegroundColor Red
    exit 1
}

# Returns $true when the given command runs Python 3.13.
function Test-Python313([string]$Exe, [string[]]$Prefix) {
    if (-not (Get-Command $Exe -ErrorAction SilentlyContinue)) { return $false }
    $out = & $Exe @Prefix -c $versionCheck 2>$null
    return ($LASTEXITCODE -eq 0 -and ([string]$out).Trim() -eq '313')
}

Set-Location $portalDir

# ---- 1. Python 3.13 and the virtual environment -------------------------------------------
if ((Test-Path $venvPython) -and -not (Test-Python313 $venvPython @())) {
    Stop-Start ("web-demo\.venv was made with a different Python version. Delete the folder " +
        "'$venvDir' and run this script again.")
}

if (-not (Test-Path $venvPython)) {
    $candidates = @(
        @{ Exe = 'py'; Prefix = @('-3.13') },
        @{ Exe = 'python3.13'; Prefix = @() },
        @{ Exe = 'python'; Prefix = @() }
    )
    $basePython = $null
    foreach ($candidate in $candidates) {
        if (Test-Python313 $candidate.Exe $candidate.Prefix) { $basePython = $candidate; break }
    }
    if ($null -eq $basePython) {
        Stop-Start ("Python 3.13 was not found. Install it with 'winget install Python.Python.3.13' " +
            "(or 'uv python install 3.13'), open a new terminal, and run this script again.")
    }
    $baseLabel = (@($basePython.Exe) + $basePython.Prefix) -join ' '
    Write-Step "Creating the virtual environment with '$baseLabel' (first run only)..."
    $basePrefix = $basePython.Prefix
    & $basePython.Exe @basePrefix -m venv $venvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        Stop-Start "Could not create the virtual environment in '$venvDir'."
    }
}

$pythonVersion = (& $venvPython --version 2>&1 | Out-String).Trim()
Write-Step "Using $pythonVersion ($venvPython)"

# ---- 2. Pinned packages ---------------------------------------------------------------------
$wanted = (Get-FileHash -Algorithm SHA256 -LiteralPath $requirements).Hash
$installed = ''
if (Test-Path $marker) { $installed = ([System.IO.File]::ReadAllText($marker)).Trim() }
if ($installed -ne $wanted) {
    Write-Step 'Installing pinned packages from requirements.txt (this can take a few minutes)...'
    & $venvPython -m pip --version *> $null
    if ($LASTEXITCODE -ne 0) {
        & $venvPython -m ensurepip --upgrade
    }
    & $venvPython -m pip install --disable-pip-version-check --requirement $requirements
    if ($LASTEXITCODE -ne 0) {
        Stop-Start 'Package installation failed (see the messages above). Check the network and try again.'
    }
    [System.IO.File]::WriteAllText($marker, $wanted)
}
else {
    Write-Step 'Pinned packages already installed.'
}

# ---- 3. Gemini API key (value is never printed) ---------------------------------------------
if ([string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) {
    # A terminal opened before the key was saved does not see it; read the saved user value.
    $savedKey = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
    if (-not [string]::IsNullOrWhiteSpace($savedKey)) { $env:GEMINI_API_KEY = $savedKey }
    Remove-Variable savedKey
}
if ([string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) {
    Write-Host '[portal] Gemini API key: not configured (Part 1B live analysis will explain this; everything else works)' -ForegroundColor Yellow
}
else {
    Write-Host '[portal] Gemini API key: configured (value hidden)' -ForegroundColor Green
}

# ---- 4. Serve on 127.0.0.1 ------------------------------------------------------------------
try {
    $probe = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
    $probe.Start()
    $probe.Stop()
}
catch {
    Stop-Start ("Port $Port is already in use (is the portal already running in another window?). " +
        "Close it, or choose another port: .\start.ps1 -Port 8001")
}

$url = "http://127.0.0.1:$Port/"
$opener = $null
if (-not $NoBrowser) {
    # Background job: wait until the portal answers, then open the default browser.
    $opener = Start-Job -ArgumentList $url -ScriptBlock {
        param($Url)
        for ($i = 0; $i -lt 120; $i++) {
            try {
                $null = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri ($Url + 'api/health')
                Start-Process $Url
                return
            }
            catch { Start-Sleep -Milliseconds 500 }
        }
    }
}

Write-Step "Portal: $url  (only this computer can reach it; press Ctrl+C to stop)"
try {
    & $venvPython -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port $Port --no-access-log
    $serverExit = $LASTEXITCODE
}
finally {
    if ($null -ne $opener) { Remove-Job -Job $opener -Force -ErrorAction SilentlyContinue }
}
exit $serverExit
