$ErrorActionPreference = "Stop"

$Script = "C:\XAU_ELITE_AI\ATALHOS_LEON\scripts\atualizar_ddns_leon.ps1"
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Script`""
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
    -Description "Atualiza o endereco DuckDNS do painel LEON." `
    -Force | Out-Null

Write-Output "Tarefa LEON DDNS criada."
