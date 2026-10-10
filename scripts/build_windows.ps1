param()
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create the project .venv first (README).' }
Push-Location -LiteralPath $projectRoot
$originalPath = $env:PATH
try {
    # Prevent DLL discovery from picking incompatible tools installed on PATH.
    $pythonBase = & $pythonPath -c "import sys; print(sys.base_prefix)"
    $env:PATH = @((Split-Path $pythonPath), $pythonBase, (Join-Path $env:WINDIR 'System32'), $env:WINDIR) -join ';'
    & $pythonPath -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
    & $pythonPath -m PyInstaller --clean --noconfirm Studium.spec
    if ($LASTEXITCODE -ne 0) { throw 'Windows build failed.' }
    $exePath = Join-Path $projectRoot 'dist\Studium\Studium.exe'
    if (-not (Test-Path -LiteralPath $exePath)) { throw 'Studium.exe was not produced.' }
    Get-Item -LiteralPath $exePath | Select-Object FullName, Length
    $bundleSize = (Get-ChildItem -LiteralPath (Join-Path $projectRoot 'dist\Studium') -Recurse -File | Measure-Object Length -Sum).Sum
    Write-Output "Complete portable folder size: $bundleSize bytes. Copy the entire dist\Studium folder."
} finally {
    $env:PATH = $originalPath
    Pop-Location
}
