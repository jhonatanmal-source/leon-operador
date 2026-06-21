$ErrorActionPreference = "Stop"

$Root = "C:\XAU_ELITE_AI"
$EnvFile = Join-Path $Root ".env"

function Read-Secret {
    param([string]$Prompt)

    $secure = Read-Host $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$Hostname = (Read-Host "Hostname completo No-IP (ex: leonoperador.ddns.net)").Trim()
$Username = (Read-Host "Usuario da DDNS Key No-IP").Trim()
$Password = (Read-Secret "Senha da DDNS Key No-IP").Trim()

if (-not $Hostname -or -not $Username -or -not $Password) {
    throw "Hostname e credenciais da DDNS Key sao obrigatorios."
}

$Values = @{
    "LEON_DDNS_PROVIDER" = "noip"
    "LEON_NOIP_HOSTNAME" = $Hostname.ToLower()
    "LEON_NOIP_DDNS_USERNAME" = $Username
    "LEON_NOIP_DDNS_PASSWORD" = $Password
}
$Lines = if (Test-Path $EnvFile) {
    Get-Content -LiteralPath $EnvFile
} else {
    @()
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

$Updater = Join-Path `
    $Root `
    "ATALHOS_LEON\scripts\atualizar_noip_leon.ps1"
& $Updater

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument (
        "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass " +
        "-File `"$Updater`""
    )
$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "LEON DDNS" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Atualiza o hostname No-IP do painel LEON." `
    -Force | Out-Null

Write-Output ""
Write-Output "No-IP configurado: $Hostname"
Write-Output "Confirme o hostname na conta No-IP quando solicitado."
