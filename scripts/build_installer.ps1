Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Push-Location $ProjectRoot

try {
    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    $Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

    $Version = & $Python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
    & $Python -m PyInstaller --clean --noconfirm "packaging\pyinstaller\eml_viewer.spec"

    $IsccCandidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    $Iscc = $null
    foreach ($Candidate in $IsccCandidates) {
        if (Test-Path $Candidate) {
            $Iscc = $Candidate
            break
        }
    }
    if ($null -eq $Iscc) {
        $Command = Get-Command iscc -ErrorAction SilentlyContinue
        if ($Command) {
            $Iscc = $Command.Source
        }
    }
    if ($null -eq $Iscc) {
        throw "Could not find Inno Setup 6 ISCC.exe. Please install Inno Setup 6 and run again."
    }

    New-Item -ItemType Directory -Force -Path "installer" | Out-Null
    & $Iscc "/DMyAppVersion=$Version" "packaging\inno\eml_viewer.iss"
    Write-Host "Installer complete: installer\EmlViewerSetup-$Version.exe"
}
finally {
    Pop-Location
}
