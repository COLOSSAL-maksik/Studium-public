[CmdletBinding()]
param(
    [switch]$SkipAppBuild,
    [string]$InnoSetupCompiler
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
function Assert-UnlinkedPath([string]$Path) {
    $cursor = $Path
    while ($cursor) {
        $item = $null
        try { $item = Get-Item -LiteralPath $cursor -Force -ErrorAction Stop }
        catch [System.Management.Automation.ItemNotFoundException] { }
        if ($item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Linked build/output/staging paths are not supported.'
        }
        $cursor = Split-Path -Path $cursor -Parent
    }
}
function Assert-UnlinkedStageTree([string]$StagePath) {
    Assert-UnlinkedPath $StagePath
    $pending = [Collections.Generic.Stack[string]]::new()
    $pending.Push($StagePath)
    while ($pending.Count) {
        $directory = $pending.Pop()
        foreach ($item in (Get-ChildItem -LiteralPath $directory -Force)) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Staging contains a link; cleanup refused.'
            }
            if ($item.PSIsContainer) { $pending.Push($item.FullName) }
        }
    }
}
if ($env:OS -ne 'Windows_NT') { throw 'Installer compilation requires native Windows.' }
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { throw 'Create the project .venv first (README).' }
if (-not $InnoSetupCompiler) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { $InnoSetupCompiler = $command.Source }
    else {
        foreach ($base in @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA)) {
            if (-not $base) { continue }
            $candidate = Join-Path $base 'Inno Setup 6\ISCC.exe'
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { $InnoSetupCompiler = $candidate; break }
        }
        if (-not $InnoSetupCompiler -and $env:LOCALAPPDATA) {
            $candidate = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { $InnoSetupCompiler = $candidate }
        }
    }
}
if (-not $InnoSetupCompiler -or -not (Test-Path -LiteralPath $InnoSetupCompiler -PathType Leaf)) {
    throw 'Install Inno Setup 6.3+ separately, or pass -InnoSetupCompiler C:\path\ISCC.exe.'
}
$InnoSetupCompiler = (Resolve-Path -LiteralPath $InnoSetupCompiler).Path
# ISCC's launcher FileVersion is not the Inno engine version. Studium.iss checks
# the authoritative ISPP version and the compiler validates its required features.
$checker = Join-Path $PSScriptRoot 'check_windows_bundle.py'
$appVersion = & $pythonPath $checker --version
if ($LASTEXITCODE -ne 0) { throw 'Application version validation failed.' }
$bundle = Join-Path $projectRoot 'dist\Studium'
$buildRoot = Join-Path $projectRoot 'build'
$outputRoot = Join-Path $projectRoot 'dist\installers'
# Reject redirections before creating or deleting anything. Cleanup owns only this unique stage.
foreach ($target in @($buildRoot, $outputRoot, $bundle)) {
    Assert-UnlinkedPath $target
}
if (-not $SkipAppBuild) { & (Join-Path $PSScriptRoot 'build_windows.ps1') }
$exe = Join-Path $bundle 'Studium.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Missing dist\Studium\Studium.exe. Run scripts\build_windows.ps1 first.' }
if ((Get-Item -LiteralPath $exe).VersionInfo.ProductVersion -ne $appVersion) {
    throw 'The onedir version is stale or unversioned. Rebuild with scripts\build_windows.ps1.'
}
New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null
$stage = Join-Path $buildRoot ('installer-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    & $pythonPath $checker --bundle $bundle --stage $stage
    if ($LASTEXITCODE -ne 0) { throw 'Payload audit failed; installer was not compiled.' }
    $compiled = Join-Path $stage 'output'
    & $InnoSetupCompiler "/DAppVersion=$appVersion" "/DPayloadInclude=$(Join-Path $stage 'payload.iss')" "/O$compiled" (Join-Path $projectRoot 'installer\Studium.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
    $fileName = "Studium-Setup-$appVersion.exe"
    $result = Join-Path $compiled $fileName
    if (-not (Test-Path -LiteralPath $result -PathType Leaf)) { throw 'Inno Setup did not produce the expected installer.' }
    Assert-UnlinkedPath $outputRoot
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
    $destination = Join-Path $outputRoot $fileName
    $manifestDestination = Join-Path $outputRoot "Studium-Setup-$appVersion.payload.json"
    foreach ($target in @($destination, $manifestDestination, "$destination.sha256")) {
        Assert-UnlinkedPath $target
    }
    Move-Item -LiteralPath $result -Destination $destination -Force
    Copy-Item -LiteralPath (Join-Path $stage 'payload-manifest.json') -Destination $manifestDestination -Force
    $hash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText("$destination.sha256", "$hash  $fileName`n", [Text.Encoding]::ASCII)
    Write-Output "Installer: $destination"
    Write-Output "SHA-256: $hash"
} finally {
    # Inspect entries without recursive traversal through reparse points before deletion.
    Assert-UnlinkedStageTree $stage
    Remove-Item -LiteralPath $stage -Recurse -Force
}
