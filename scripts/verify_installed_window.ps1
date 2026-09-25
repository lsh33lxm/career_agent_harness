[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallRoot,
    [int]$CdpPort = 9234,
    [string]$ArtifactRoot,
    [switch]$UseFixture
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$InstallRoot = (Resolve-Path $InstallRoot).Path
if (-not $ArtifactRoot) { $ArtifactRoot = Join-Path $repoRoot ("artifacts\verification\installed-window-" + (Get-Date -Format "yyyyMMdd-HHmmss")) }
$ArtifactRoot = [IO.Path]::GetFullPath($ArtifactRoot)
$dataRoot = Join-Path $ArtifactRoot "data"
$e2eRoot = Join-Path $ArtifactRoot "installed-window-e2e"
New-Item -ItemType Directory -Path $dataRoot,$e2eRoot -Force | Out-Null
$exe = Join-Path $InstallRoot "agent-career-harness-desktop.exe"
if (-not (Test-Path $exe)) { throw "Installed desktop executable not found: $exe" }

$env:ACH_DESKTOP_DEMO = "1"
$env:ACH_DATA_DIR = $dataRoot
$env:INSTALLED_WINDOW_USE_FIXTURE = if ($UseFixture) { "1" } else { "0" }
$env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS = "--remote-debugging-port=$CdpPort"
$desktop = Start-Process -FilePath $exe -WorkingDirectory $InstallRoot -PassThru -WindowStyle Hidden
try {
    $cdpReady = $false
    foreach ($attempt in 1..60) {
        try { $version = Invoke-RestMethod "http://127.0.0.1:$CdpPort/json/version" -TimeoutSec 1; $cdpReady = $true; break }
        catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $cdpReady) { throw "WebView2 CDP did not become ready on port $CdpPort" }
    $env:CDP_PORT = "$CdpPort"
    $env:INSTALLED_WINDOW_ARTIFACT_DIR = $e2eRoot
    & (Get-Command node.exe).Source (Join-Path $repoRoot "scripts\probe_installed_window.mjs") *>&1 | Tee-Object -FilePath (Join-Path $ArtifactRoot "installed-window-e2e.txt")
    if ($LASTEXITCODE -ne 0) { throw "Installed window probe failed with exit code $LASTEXITCODE" }
    Start-Sleep -Seconds 2
    $desktop.Refresh()
    $sidecars = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -like "agent-career-harness-sidecar*" -and $_.CommandLine -like "*$dataRoot*" })
    $result = if ($desktop.HasExited -and $sidecars.Count -eq 0) { "passed" } else { "failed_teardown" }
    [ordered]@{ installer_root = $InstallRoot; artifact_root = $ArtifactRoot; cdp_port = $CdpPort; use_fixture = [bool]$UseFixture; desktop_pid = $desktop.Id; desktop_exited = $desktop.HasExited; desktop_exit_code = if ($desktop.HasExited) { $desktop.ExitCode } else { $null }; sidecar_count = $sidecars.Count; result = $result } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $ArtifactRoot "installed-window-summary.json") -Encoding UTF8
    if ($result -ne "passed") { throw "Installed window teardown failed" }
    Write-Output "RESULT=passed"
    Write-Output "ARTIFACTS=$ArtifactRoot"
}
finally {
    Remove-Item Env:ACH_DESKTOP_DEMO,Env:ACH_DATA_DIR,Env:INSTALLED_WINDOW_USE_FIXTURE,Env:WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS,Env:CDP_PORT,Env:INSTALLED_WINDOW_ARTIFACT_DIR -ErrorAction SilentlyContinue
}
