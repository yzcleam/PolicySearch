$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"

function Get-DotEnvValue($path, $key, $default) {
    if (Test-Path $path) {
        $pattern = "^\s*" + [regex]::Escape($key) + "\s*="
        $line = Get-Content $path | Where-Object { $_ -match $pattern } | Select-Object -First 1
        if ($line) {
            return (($line -split "=", 2)[1].Trim().Trim('"').Trim("'"))
        }
    }
    return $default
}

$distro = if ($env:WSL_DISTRO) { $env:WSL_DISTRO } else { Get-DotEnvValue $envFile "WSL_DISTRO" "Ubuntu" }
$appPort = Get-DotEnvValue $envFile "APP_PORT" "8000"

if ($root -notmatch "^[A-Za-z]:\\") {
    throw "This helper expects the project on a Windows drive (for example C:\Projects\PolicySearcher)."
}
$wslRoot = "/mnt/" + $root.Substring(0, 1).ToLower() + (($root.Substring(2) -replace "\\", "/"))
$composeFile = "$wslRoot/docker-compose.yml"
$dockerSh = "$wslRoot/scripts/wsl/docker.sh"

Write-Host "Stopping FastAPI on port $appPort ..."
$listener = Get-NetTCPConnection -LocalPort $appPort -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    Stop-Process -Id $listener.OwningProcess -Force
}

Write-Host "Stopping PostgreSQL and OpenSearch (volumes are kept) ..."
wsl -d $distro -- bash $dockerSh compose -f $composeFile -p policysearcher down 2>$null

Write-Host "Done. Run 'wsl --terminate $distro' if you also want to stop the WSL distro."
