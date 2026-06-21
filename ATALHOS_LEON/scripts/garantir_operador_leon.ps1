$ErrorActionPreference = "Stop"

$Root = "C:\XAU_ELITE_AI"
$Log = Join-Path $Root "logs\operator_runtime.log"
$ErrorLog = Join-Path $Root "logs\operator_runtime_error.log"

$running = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -like "python*" -and
        $_.CommandLine -match "src[\\/]leon_operator\.py" -and
        $_.CommandLine -notmatch "--grant-autonomy|--send-status|--status-autonomy"
    } |
    Select-Object -First 1

if ($running) {
    exit 0
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs") |
    Out-Null

Start-Process `
    -FilePath "python" `
    -ArgumentList "-B", "src\leon_operator.py" `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $Log `
    -RedirectStandardError $ErrorLog `
    -WindowStyle Hidden
