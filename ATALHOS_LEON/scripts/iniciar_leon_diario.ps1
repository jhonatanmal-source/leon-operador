$ErrorActionPreference = "Stop"

$Root = "C:\XAU_ELITE_AI"
$Logs = Join-Path $Root "logs"
$Data = Join-Path $Root "data"
$Cloudflared = Join-Path $Root "tools\cloudflared.exe"
$Tailscale = "C:\Program Files\Tailscale\tailscale.exe"
$FixedUrl = "https://leon-operador.tailcdf4e1.ts.net/login"
$WebLog = Join-Path $Logs "web_collab_runtime.log"
$WebErrorLog = Join-Path $Logs "web_collab_runtime_error.log"
$TunnelLog = Join-Path $Logs "web_tunnel_runtime.log"
$TunnelErrorLog = Join-Path $Logs "web_tunnel_runtime_error.log"
$CurrentUrlFile = Join-Path $Data "link_painel_web.txt"
$DesktopFolder = Join-Path `
    ([Environment]::GetFolderPath("Desktop")) `
    "LEON - ATALHOS"
$DesktopShortcut = Join-Path $DesktopFolder "LEON WEB COLLAB.url"

New-Item -ItemType Directory -Force -Path $Logs, $Data | Out-Null
New-Item -ItemType Directory -Force -Path $DesktopFolder | Out-Null

$webRunning = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match "web_app\\app.py" } |
    Select-Object -First 1

if (-not $webRunning) {
    Start-Process `
        -FilePath "python" `
        -ArgumentList "-B", "web_app\app.py" `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $WebLog `
        -RedirectStandardError $WebErrorLog `
        -WindowStyle Hidden
}

$localDeadline = (Get-Date).AddSeconds(20)
do {
    try {
        $localReady = (Invoke-WebRequest `
            -Uri "http://127.0.0.1:5000/login" `
            -UseBasicParsing `
            -TimeoutSec 3).StatusCode -eq 200
    }
    catch {
        $localReady = $false
    }
    if (-not $localReady) {
        Start-Sleep -Seconds 2
    }
} while (-not $localReady -and (Get-Date) -lt $localDeadline)

# Tailscale Funnel supplies the permanent HTTPS address without router ports.
$tailscaleReady = $false
if ($localReady -and (Test-Path $Tailscale)) {
    $service = Get-Service -Name "Tailscale" -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne "Running") {
        Start-Service -Name "Tailscale"
        Start-Sleep -Seconds 3
    }

    $funnelStatus = & $Tailscale funnel status --json 2>$null | Out-String
    if ($funnelStatus -notmatch '"Proxy"\s*:\s*"http://127\.0\.0\.1:5000"') {
        Start-Process `
            -FilePath $Tailscale `
            -ArgumentList "funnel", "--bg", "--yes", "5000" `
            -WindowStyle Hidden `
            -Wait
    }

    try {
        $tailscaleReady = (Invoke-WebRequest `
            -Uri $FixedUrl `
            -UseBasicParsing `
            -TimeoutSec 20).StatusCode -eq 200
    }
    catch {
        $tailscaleReady = $false
    }
}

if ($tailscaleReady) {
    Set-Content -LiteralPath $CurrentUrlFile -Value $FixedUrl -Encoding ASCII
    Set-Content `
        -LiteralPath $DesktopShortcut `
        -Value "[InternetShortcut]`r`nURL=$FixedUrl`r`n" `
        -Encoding ASCII
    exit 0
}

# Keep Quick Tunnel as an automatic contingency if Tailscale is unavailable.
$tunnelRunning = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq "cloudflared.exe" -and
        $_.CommandLine -match "127.0.0.1:5000"
    } |
    Select-Object -First 1

if (-not $tunnelRunning) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $TunnelLog = Join-Path $Logs "web_tunnel_runtime_$stamp.log"
    $TunnelErrorLog = Join-Path $Logs "web_tunnel_runtime_error_$stamp.log"
    Start-Process `
        -FilePath $Cloudflared `
        -ArgumentList "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:5000" `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $TunnelLog `
        -RedirectStandardError $TunnelErrorLog `
        -WindowStyle Hidden
}

$deadline = (Get-Date).AddSeconds(30)
$remoteUrl = $null
while ((Get-Date) -lt $deadline -and -not $remoteUrl) {
    Start-Sleep -Seconds 2
    foreach ($path in @($TunnelLog, $TunnelErrorLog)) {
        if (-not (Test-Path $path)) {
            continue
        }
        $match = Select-String `
            -Path $path `
            -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" `
            -AllMatches |
            Select-Object -Last 1
        if ($match) {
            $remoteUrl = $match.Matches.Value
            break
        }
    }
}

if ($remoteUrl) {
    $loginUrl = "$remoteUrl/login"
    # ASCII avoids the UTF-8 BOM that cmd.exe would treat as part of the URL.
    Set-Content -LiteralPath $CurrentUrlFile -Value $loginUrl -Encoding ASCII
    Set-Content `
        -LiteralPath $DesktopShortcut `
        -Value "[InternetShortcut]`r`nURL=$loginUrl`r`n" `
        -Encoding ASCII
}
