Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Push-Location $ProjectRoot

try {
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    $Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

    & $Python -m PyInstaller --clean --noconfirm "packaging\pyinstaller\eml_viewer.spec"
    Write-Host "Build complete: dist\EmlViewer"
}
finally {
    Pop-Location
}
