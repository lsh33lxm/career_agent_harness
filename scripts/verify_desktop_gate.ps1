[CmdletBinding()]
param(
    [string]$Python = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = (Resolve-Path (Join-Path $repoRoot $Python)).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$artifactRoot = Join-Path $repoRoot "artifacts\verification\desktop-gate-$stamp"
$dataRoot = Join-Path $artifactRoot "runtime-data"
$logRoot = Join-Path $artifactRoot "logs"
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$ownedProcesses = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()

function Get-FreeLoopbackPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try { return $listener.LocalEndpoint.Port }
    finally { $listener.Stop() }
}

function Start-TrackedProcess([string]$FilePath, [string]$Arguments, [string]$Name, [string]$WorkingDirectory = $repoRoot) {
    $stdout = Join-Path $logRoot "$Name.stdout.log"
    $stderr = Join-Path $logRoot "$Name.stderr.log"
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    $ownedProcesses.Add($process)
    return $process
}

function Stop-TrackedProcess([System.Diagnostics.Process]$Process) {
    if ($null -eq $Process) { return }
    try {
        $Process.Refresh()
        if (-not $Process.HasExited) {
            $all = @(Get-CimInstance Win32_Process)
            $ownedIds = [System.Collections.Generic.HashSet[int]]::new()
            [void]$ownedIds.Add($Process.Id)
            do {
                $added = $false
                foreach ($child in $all) {
                    if ($ownedIds.Contains([int]$child.ParentProcessId) -and $ownedIds.Add([int]$child.ProcessId)) { $added = $true }
                }
            } while ($added)
            foreach ($id in @($ownedIds | Where-Object { $_ -ne $Process.Id } | Sort-Object -Descending)) {
                Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            }
            Stop-Process -Id $Process.Id -Force
            $Process.WaitForExit(10000) | Out-Null
        }
        $Process.Refresh()
        if (-not $Process.HasExited) { throw "Owned process $($Process.Id) did not exit." }
    } catch {
        Write-Warning "Could not confirm cleanup of owned process $($Process.Id): $_"
        throw
    }
}

function Wait-Http([string]$Url, [int]$TimeoutSeconds, [string]$Name) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Milliseconds 250
    }
    throw "$Name did not become ready: $Url"
}

function Invoke-E2E([string]$Grep) {
    $playwrightCli = Join-Path $repoRoot "node_modules\@playwright\test\cli.js"
    Write-Output "RUN: node $playwrightCli test --config playwright.config.ts --reporter=line --grep `"$Grep`""
    Push-Location (Join-Path $repoRoot "apps\desktop")
    try { & (Get-Command node.exe).Source $playwrightCli test --config playwright.config.ts --reporter=line --grep $Grep --global-timeout=120000 }
    finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { throw "Playwright failed for: $Grep (exit $LASTEXITCODE)" }
}

$apiPort = Get-FreeLoopbackPort
do { $webPort = Get-FreeLoopbackPort } while ($webPort -eq $apiPort)
$env:ACH_ENV = "demo"
$env:PYTHONPATH = Join-Path $repoRoot "backend"
$env:ACH_DATA_DIR = $dataRoot
$env:ACH_HOST = "127.0.0.1"
$env:ACH_PORT = "$apiPort"
$env:ACH_ALLOWED_ORIGIN = "http://127.0.0.1:$webPort"
$env:ACH_VERIFY_API_PORT = "$apiPort"
$env:ACH_VERIFY_WEB_PORT = "$webPort"
$env:ACH_VERIFY_ARTIFACT_DIR = $artifactRoot
$cachedChromium = Join-Path $env:LOCALAPPDATA "ms-playwright\chromium-1234\chrome-win64\chrome.exe"
if (Test-Path -LiteralPath $cachedChromium) { $env:ACH_VERIFY_CHROMIUM_PATH = $cachedChromium }

$apiProcess = $null
$webProcess = $null
try {
    $apiProcess = Start-TrackedProcess $pythonPath "-m career_harness --host 127.0.0.1 --port $apiPort --environment demo" "api"
    Wait-Http "http://127.0.0.1:$apiPort/health" 30 "Demo API"
    $desktopRoot = Join-Path $repoRoot "apps\desktop"
    $viteScript = Join-Path $repoRoot "node_modules\vite\bin\vite.js"
    $webProcess = Start-TrackedProcess (Get-Command node.exe).Source `
        "`"$viteScript`" --host 127.0.0.1 --port $webPort --strictPort" "vite" $desktopRoot
    Wait-Http "http://127.0.0.1:$webPort/" 30 "Vite"

    Write-Output "VERIFY: full visible UI flow; API=$apiPort, Web=$webPort, ACH_DATA_DIR=$dataRoot"
    Invoke-E2E "Resume Review Gate full UI flow persists through refresh"

    Stop-TrackedProcess $apiProcess
    $apiProcess = Start-TrackedProcess $pythonPath "-m career_harness --host 127.0.0.1 --port $apiPort --environment demo" "api-restarted"
    Wait-Http "http://127.0.0.1:$apiPort/health" 30 "Restarted Demo API"
    Invoke-E2E "API restart preserves the reviewed revision in History and Knowledge"
    Invoke-E2E "API unavailable keeps Demo Mode usable and reports Chinese recovery text"

    $summary = @{
        timestamp = (Get-Date).ToString("o")
        demo_data_directory = $dataRoot
        api_port = $apiPort
        web_port = $webPort
        api_pid_initial = $ownedProcesses[0].Id
        api_pid_restarted = $apiProcess.Id
        vite_pid = $webProcess.Id
        chromium_executable = $env:ACH_VERIFY_CHROMIUM_PATH
        result = "passed"
    } | ConvertTo-Json -Depth 4
    Set-Content -LiteralPath (Join-Path $artifactRoot "run-summary.json") -Value $summary -Encoding UTF8
    Write-Output "ARTIFACTS=$artifactRoot"
    Write-Output "RESULT=passed"
}
finally {
    foreach ($process in $ownedProcesses) { Stop-TrackedProcess $process }
    if (Test-Path -LiteralPath $dataRoot) { Remove-Item -LiteralPath $dataRoot -Recurse -Force }
    Remove-Item Env:\ACH_ENV, Env:\ACH_DATA_DIR, Env:\ACH_HOST, Env:\ACH_PORT, Env:\ACH_ALLOWED_ORIGIN, Env:\PYTHONPATH, `
        Env:\ACH_VERIFY_API_PORT, Env:\ACH_VERIFY_WEB_PORT, Env:\ACH_VERIFY_ARTIFACT_DIR, Env:\ACH_VERIFY_CHROMIUM_PATH -ErrorAction SilentlyContinue
}
