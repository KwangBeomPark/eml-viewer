Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Push-Location $ProjectRoot

try {
    python -m PyInstaller --clean --noconfirm "packaging\pyinstaller\eml_viewer.spec"
    Write-Host "Build complete: dist\EmlViewer"
}
finally {
    Pop-Location
}
