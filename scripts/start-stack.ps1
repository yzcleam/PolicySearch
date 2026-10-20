$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$distro = "Ubuntu-Clean"
$composeFile = "/mnt/e/PolicySearcher/docker-compose.yml"
$dockerSh = "/mnt/e/PolicySearcher/scripts/wsl/docker.sh"
$python = Join-Path $root ".venv\Scripts\python.exe"
$backend = Join-Path $root "backend"

Write-Host "[1/5] Booting WSL distro $distro ..."
# Keep the distro (and therefore Docker) alive between commands.
wsl -d $distro -- bash -lc "pgrep -f 'sleep infinity' >/dev/null || (nohup sleep infinity >/dev/null 2>&1 &)" 2>$null | Out-Null

$dockerState = (wsl -d $distro -- bash -lc "systemctl is-active docker" 2>&1 | Out-String).Trim()
if ($dockerState -notmatch "active") {
    throw "Docker is not active inside $distro. Check: wsl -d $distro -- systemctl status docker"
}

Write-Host "[2/5] Starting PostgreSQL and OpenSearch ..."
wsl -d $distro -- bash $dockerSh compose -f $composeFile -p policysearcher up -d 2>$null

Write-Host "[3/5] Waiting for OpenSearch to become healthy ..."
$healthy = $false
for ($i = 0; $i -lt 45; $i++) {
    $status = (wsl -d $distro -- docker inspect -f "{{.State.Health.Status}}" policy-opensearch 2>$null | Out-String).Trim()
    if ($status -eq "healthy") {
        $healthy = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $healthy) {
    throw "OpenSearch did not become healthy in time. Check: wsl -d $distro -- docker logs --tail 80 policy-opensearch"
}

Write-Host "[4/5] Starting FastAPI ..."
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    Start-Process -FilePath $python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $backend -WindowStyle Hidden
}

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 3 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ready) {
    throw "FastAPI did not start on http://127.0.0.1:8000/"
}

Write-Host "[5/5] Stack ready. Opening http://127.0.0.1:8000/"
Start-Process "http://127.0.0.1:8000/"
