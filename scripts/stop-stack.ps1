$ErrorActionPreference = "Continue"

$distro = "Ubuntu-Clean"
$composeFile = "/mnt/e/PolicySearcher/docker-compose.yml"
$dockerSh = "/mnt/e/PolicySearcher/scripts/wsl/docker.sh"

Write-Host "Stopping FastAPI on port 8000 ..."
$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Stop-Process -Id $listener.OwningProcess -Force
}

Write-Host "Stopping PostgreSQL and OpenSearch (volumes are kept) ..."
wsl -d $distro -- bash $dockerSh compose -f $composeFile -p policysearcher down 2>$null

Write-Host "Done. Run 'wsl --terminate $distro' if you also want to stop the WSL distro."
