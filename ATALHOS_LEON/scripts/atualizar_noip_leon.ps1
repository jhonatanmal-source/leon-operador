$ErrorActionPreference = "Stop"

$Root = "C:\XAU_ELITE_AI"
$EnvFile = Join-Path $Root ".env"
$LogFile = Join-Path $Root "logs\ddns_leon.log"

function Read-EnvValue {
    param([string]$Name)

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

$Hostname = Read-EnvValue "LEON_NOIP_HOSTNAME"
$Username = Read-EnvValue "LEON_NOIP_DDNS_USERNAME"
$Password = Read-EnvValue "LEON_NOIP_DDNS_PASSWORD"

if (-not $Hostname -or -not $Username -or -not $Password) {
    throw "Configure hostname, usuario e senha da DDNS Key No-IP."
}

$PublicIp = (Invoke-RestMethod `
    -Uri "https://api.ipify.org?format=json" `
    -TimeoutSec 15).ip

$Pair = "${Username}:${Password}"
$Basic = [Convert]::ToBase64String(
    [Text.Encoding]::ASCII.GetBytes($Pair)
)
$Headers = @{
    Authorization = "Basic $Basic"
    "User-Agent" = "LEON-XAU-DDNS/1.0 admin@localhost"
}
$UpdateUrl = (
    "https://dynupdate.no-ip.com/nic/update" +
    "?hostname=$([uri]::EscapeDataString($Hostname))" +
    "&myip=$([uri]::EscapeDataString($PublicIp))"
)

$Result = Invoke-RestMethod `
    -Uri $UpdateUrl `
    -Headers $Headers `
    -TimeoutSec 20
$ResultText = "$Result".Trim()
$Accepted = (
    $ResultText.StartsWith("good ") -or
    $ResultText.StartsWith("nochg ")
)

New-Item `
    -ItemType Directory `
    -Force `
    -Path (Split-Path $LogFile) | Out-Null
Add-Content `
    -LiteralPath $LogFile `
    -Value (
        "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | " +
        "provider=No-IP | hostname=$Hostname | ip=$PublicIp | " +
        "result=$ResultText"
    )

if (-not $Accepted) {
    throw "No-IP recusou a atualizacao: $ResultText"
}

Write-Output "No-IP atualizado: $Hostname -> $PublicIp"
