param(
    [string]$Python = "python",
    [switch]$InstallPythonPackages
)

$ErrorActionPreference = "Stop"
$skillRoot = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $PSScriptRoot "open_imagegen.py"
$requirements = Join-Path $skillRoot "requirements.txt"

if ($InstallPythonPackages) {
    & $Python -m pip install --upgrade -r $requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Python package installation failed."
    }
}

Write-Output "PyTorch and its matching torchvision build are intentionally not pinned here; install a CUDA-compatible pair for this machine."

& $Python $runtime doctor
if ($LASTEXITCODE -ne 0) {
    throw "Open ImageGen doctor failed. Install a CUDA-enabled PyTorch build matching the NVIDIA driver, then rerun setup."
}

Write-Output "Open ImageGen runtime is ready. Model weights download on first use or via the download command."
