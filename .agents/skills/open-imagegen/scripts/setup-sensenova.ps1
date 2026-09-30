param(
    [string]$Python = "python",
    [string]$VenvPath = ".local\venvs\open-imagegen-sensenova"
)

$ErrorActionPreference = "Stop"
$skillRoot = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $PSScriptRoot "open_imagegen.py"
$requirements = Join-Path $skillRoot "requirements-sensenova.txt"

if (-not (Test-Path -LiteralPath $VenvPath)) {
    & $Python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) {
        throw "SenseNova virtual environment creation failed."
    }
}

$venvPython = Join-Path $VenvPath "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install --index-url https://download.pytorch.org/whl/cu128 torch==2.8.0 torchvision==0.23.0
& $venvPython -m pip install --upgrade -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw "SenseNova package installation failed."
}

& $venvPython $runtime doctor
if ($LASTEXITCODE -ne 0) {
    throw "Open ImageGen doctor failed in the SenseNova environment."
}

Write-Output "SenseNova runtime ready: $venvPython"
Write-Output "Download the quality profile with:"
Write-Output "& '$venvPython' '$runtime' download --model sensenova-u1.5-q8"
