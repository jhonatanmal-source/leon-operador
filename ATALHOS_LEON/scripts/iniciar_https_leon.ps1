$ErrorActionPreference = "Stop"

$Root = "C:\XAU_ELITE_AI"
$Caddy = Join-Path $Root "tools\caddy.exe"
$Caddyfile = Join-Path $Root "config\Caddyfile"
$Logs = Join-Path $Root "logs"
$Output = Join-Path $Logs "caddy_runtime.log"
$Errors = Join-Path $Logs "caddy_runtime_error.log"

if (-not (Test-Path $Caddy)) {
    throw "Caddy nao encontrado em tools\caddy.exe."
}

$running = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq "caddy.exe" -and
        $_.CommandLine -match "config\\Caddyfile"
    } |
    Select-Object -First 1

if ($running) {
    Write-Output "Caddy HTTPS ja esta em execucao."
    exit 0
}

New-Item -ItemType Directory -Force -Path $Logs | Out-Null
Start-Process `
    -FilePath $Caddy `
    -ArgumentList "run", "--config", $Caddyfile, "--adapter", "caddyfile" `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $Output `
    -RedirectStandardError $Errors `
    -WindowStyle Hidden

Write-Output "Caddy HTTPS iniciado."
