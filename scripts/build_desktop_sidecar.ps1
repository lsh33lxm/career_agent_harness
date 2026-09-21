[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$TargetTriple
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $TargetTriple) {
    $hostLine = & rustc -vV | Where-Object { $_ -like "host: *" } | Select-Object -First 1
    if (-not $hostLine) {
        throw "Unable to determine the Rust host target with 'rustc -vV'."
    }
    $TargetTriple = $hostLine.Substring(6).Trim()
}

$buildRoot = Join-Path $repoRoot "build\desktop-sidecar"
$workPath = Join-Path $buildRoot "work"
$distPath = Join-Path $buildRoot "dist"
$specPath = Join-Path $buildRoot "spec"
$binaryDir = Join-Path $repoRoot "apps\desktop\src-tauri\binaries"
$binaryName = "agent-career-harness-sidecar-$TargetTriple.exe"
$binaryPath = Join-Path $binaryDir $binaryName

foreach ($path in @($workPath, $distPath, $specPath)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $path | Out-Null
}
New-Item -ItemType Directory -Path $binaryDir -Force | Out-Null

$entryPoint = Join-Path $repoRoot "backend\career_harness\__main__.py"
$backendPath = Join-Path $repoRoot "backend"
$alembicConfig = Join-Path $repoRoot "alembic.ini"
$migrationsPath = Join-Path $repoRoot "migrations"
$dataSeparator = [IO.Path]::PathSeparator

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name "agent-career-harness-sidecar" `
    --paths $backendPath `
    --add-data "$alembicConfig${dataSeparator}." `
    --add-data "$migrationsPath${dataSeparator}migrations" `
    --workpath $workPath `
    --distpath $distPath `
    --specpath $specPath `
    $entryPoint

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$builtBinary = Join-Path $distPath "agent-career-harness-sidecar.exe"
if (-not (Test-Path -LiteralPath $builtBinary)) {
    throw "PyInstaller did not produce the expected sidecar: $builtBinary"
}

Copy-Item -LiteralPath $builtBinary -Destination $binaryPath -Force
$hash = (Get-FileHash -LiteralPath $binaryPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "SIDECAR_PATH=$binaryPath"
Write-Output "SIDECAR_SHA256=$hash"
