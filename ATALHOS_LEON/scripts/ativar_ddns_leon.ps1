$ErrorActionPreference = "Stop"

$Root = "C:\XAU_ELITE_AI"
$EnvFile = Join-Path $Root ".env"
$Domain = Read-Host "Subdominio DuckDNS" 
$SecureToken = Read-Host "Token DuckDNS" -AsSecureString
$Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)

try {
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer)
}

if (-not $Domain -or -not $Token) {
    throw "Dominio e token sao obrigatorios."
}

$Lines = Get-Content -LiteralPath $EnvFile
$Values = @{
    "LEON_DUCKDNS_DOMAIN" = $Domain.Trim().ToLower()
    "LEON_DUCKDNS_TOKEN" = $Token.Trim()
}

foreach ($Name in $Values.Keys) {
    $Found = $false
    $Lines = foreach ($Line in $Lines) {
        if ($Line -match "^$([regex]::Escape($Name))=") {
            $Found = $true
            "$Name=$($Values[$Name])"
        } else {
            $Line
        }
    }
    if (-not $Found) {
        $Lines += "$Name=$($Values[$Name])"
    }
}

Set-Content -LiteralPath $EnvFile -Value $Lines -Encoding UTF8

& (Join-Path $Root "ATALHOS_LEON\scripts\atualizar_ddns_leon.ps1")
& (Join-Path $Root "ATALHOS_LEON\scripts\configurar_ddns_leon.ps1")

Write-Output ""
Write-Output "DDNS configurado: $Domain.duckdns.org"
Write-Output "Importante: acesso externo ainda exige tunel seguro ou porta HTTPS."
