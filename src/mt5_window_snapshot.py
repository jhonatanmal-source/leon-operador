# ===================================
# MT5 WINDOW SNAPSHOT
# ===================================

import subprocess
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
SNAPSHOT_DIR = REPORTS_DIR / "mt5_snapshots"


def capturar_print_mt5(pre_operation_id=None, ativo="XAUUSD"):

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    nome = (
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
        f"{pre_operation_id or 'PREOP'}_{ativo}_MT5.png"
    )
    caminho = SNAPSHOT_DIR / nome

    script = rf"""
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {{
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdcBlt, UInt32 nFlags);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {{
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }}
}}
"@

$process = Get-Process terminal64 -ErrorAction SilentlyContinue |
    Where-Object {{ $_.MainWindowHandle -ne 0 }} |
    Select-Object -First 1

if (-not $process) {{
    Write-Output "MT5_WINDOW_NOT_FOUND"
    exit 2
}}

$rect = New-Object Win32+RECT
[Win32]::GetWindowRect($process.MainWindowHandle, [ref]$rect) | Out-Null
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top

if ($width -le 0 -or $height -le 0) {{
    Write-Output "MT5_INVALID_WINDOW_SIZE"
    exit 3
}}

$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
$ok = [Win32]::PrintWindow($process.MainWindowHandle, $hdc, 2)
$graphics.ReleaseHdc($hdc)
$graphics.Dispose()

if (-not $ok) {{
    $bitmap.Dispose()
    Write-Output "MT5_PRINTWINDOW_FAILED"
    exit 4
}}

$bitmap.Save("{str(caminho)}", [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
Write-Output "OK"
"""

    try:
        resultado = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as erro:
        return {
            "ok": False,
            "error": "MT5_SCREENSHOT_EXCEPTION",
            "details": str(erro),
        }

    saida = (resultado.stdout or "").strip()
    erro = (resultado.stderr or "").strip()

    if resultado.returncode != 0 or not caminho.exists():
        return {
            "ok": False,
            "error": saida or "MT5_SCREENSHOT_FAILED",
            "details": erro,
            "returncode": resultado.returncode,
        }

    return {
        "ok": True,
        "path": str(caminho),
        "caption": f"Print real do MT5 | {ativo} | {pre_operation_id or 'SEM_PREOP'}",
    }
