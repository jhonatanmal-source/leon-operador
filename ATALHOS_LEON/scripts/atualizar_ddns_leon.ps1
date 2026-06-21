$ErrorActionPreference = "Stop"

$Root = "C:\XAU_ELITE_AI"
$EnvFile = Join-Path $Root ".env"
$LogFile = Join-Path $Root "logs\ddns_leon.log"

function Read-EnvValue {
    param(
        [string]$Name
    )

    if (-not (Test-Path $EnvFile)) {
        return ""
    }

    $line = Get-Content -LiteralPath $EnvFile |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=" } |
        Select-Object -Last 1

    if (-not $line) {
        return ""
    }

    return ($line -split "=", 2)[1].Trim()
}

$Domain = Read-EnvValue "LEON_DUCKDNS_DOMAIN"
$Token = Read-EnvValue "LEON_DUCKDNS_TOKEN"

if (-not $Domain -or -not $Token) {
    throw "Configure LEON_DUCKDNS_DOMAIN e LEON_DUCKDNS_TOKEN no arquivo .env."
}

$PublicIp = (Invoke-RestMethod `
    -Uri "https://api.ipify.org?format=json" `
    -TimeoutSec 15).ip

$UpdateUrl = "https://www.duckdns.org/update?domains=$Domain&token=$Token&ip=$PublicIp"
$Result = Invoke-RestMethod -Uri $UpdateUrl -TimeoutSec 20
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null
Add-Content `
    -LiteralPath $LogFile `
    -Value "$Timestamp | domain=$Domain.duckdns.org | ip=$PublicIp | result=$Result"

if ($Result -ne "OK") {
    throw "DuckDNS recusou a atualizacao: $Result"
}
