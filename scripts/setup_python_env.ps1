Param()
$ErrorActionPreference = 'Stop'

function Invoke-PythonCommand {
    param(
        [string[]] $Command,
        [string[]] $Arguments
    )
    $prefix = @()
    if ($Command.Count -gt 1) {
        $prefix = $Command[1..($Command.Count - 1)]
    }
    return & $Command[0] @prefix @Arguments
}

$RootDir = Split-Path -Parent $PSScriptRoot
$PythonVersionFile = Join-Path $RootDir '.python-version'
if (Test-Path $PythonVersionFile) {
    $PythonVersion = (Get-Content $PythonVersionFile -Raw).Trim()
} else {
    $PythonVersion = '3.9.19'
}
if ($env:PY_VERSION) {
    $PythonVersion = $env:PY_VERSION
}

$PythonCmd = @()
if ($env:PYTHON_BIN_OVERRIDE) {
    $PythonCmd = @($env:PYTHON_BIN_OVERRIDE)
} elseif (Get-Command pyenv -ErrorAction SilentlyContinue) {
    $pyenvRoot = (& pyenv root).Trim()
    $desiredPath = Join-Path $pyenvRoot "versions/$PythonVersion/python.exe"
    if (-not (Test-Path $desiredPath)) {
        Write-Host "[setup-python] Installing Python $PythonVersion via pyenv..."
        & pyenv install $PythonVersion
    }
    $PythonCmd = @($desiredPath)
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = @('py', "-$PythonVersion")
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = @('python3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = @('python')
} else {
    throw "[setup-python] Could not locate a Python executable. Install Python $PythonVersion or set PYTHON_BIN_OVERRIDE."
}

$versionScript = 'import sys; print("%d.%d.%d" % sys.version_info[:3])'
$detectedVersion = (Invoke-PythonCommand -Command $PythonCmd -Arguments @('-c', $versionScript)).Trim()
if ($detectedVersion -ne $PythonVersion) {
    throw "[setup-python] Expected Python $PythonVersion but found $detectedVersion. Set PYTHON_BIN_OVERRIDE to a $PythonVersion interpreter."
}

$VenvDir = Join-Path $RootDir '.venv'
if (Test-Path $VenvDir) {
    Write-Host "[setup-python] Reusing virtual environment at $VenvDir"
} else {
    Write-Host "[setup-python] Creating virtual environment at $VenvDir"
    Invoke-PythonCommand -Command $PythonCmd -Arguments @('-m', 'venv', $VenvDir)
}

$VenvPython = Join-Path $VenvDir 'Scripts/python.exe'
& $VenvPython -m pip install --upgrade pip | Out-Host
& $VenvPython -m pip install -r (Join-Path $RootDir 'requirements-dev.txt') | Out-Host

Write-Host "[setup-python] Environment ready. Activate with: `$env:VIRTUAL_ENV=$VenvDir; .\$VenvDir\Scripts\activate.ps1"
