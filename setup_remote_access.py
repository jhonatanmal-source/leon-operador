import os
import shutil
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"

WEB_BAT = r"""@echo off
title LEON WEB COLLAB
cd /d C:\XAU_ELITE_AI
echo ========================================
echo INICIANDO LEON WEB COLLAB
echo ========================================
python -B web_app\app.py
echo.
echo Se ocorreu erro, verifique as mensagens acima.
pause
"""

TUNNEL_BAT = r"""@echo off
title LEON CLOUDFLARE TUNNEL
cd /d C:\XAU_ELITE_AI
echo ========================================
echo INICIANDO CLOUDFLARE TUNNEL - LEON
echo ========================================
echo Copie o link https://...trycloudflare.com
echo Envie somente para operadores autorizados.
echo ========================================

if exist tools\cloudflared.exe (
    tools\cloudflared.exe tunnel --url http://127.0.0.1:5000
) else (
    cloudflared tunnel --url http://127.0.0.1:5000
)

pause
"""

REMOTE_BAT = r"""@echo off
title LEON ACESSO REMOTO
cd /d C:\XAU_ELITE_AI
echo ========================================
echo LEON ACESSO REMOTO
echo ========================================
echo Abrindo painel web unificado e Cloudflare Tunnel...
echo.

start "LEON WEB COLLAB" cmd /k ATALHOS_LEON\ACESSO_REMOTO\03_INICIAR_WEB.bat

timeout /t 3 /nobreak >nul

start "LEON CLOUDFLARE TUNNEL" cmd /k ATALHOS_LEON\ACESSO_REMOTO\04_INICIAR_TUNEL.bat

echo.
echo Duas janelas foram abertas:
echo 1 - Painel Web unificado do LEON
echo 2 - Cloudflare Tunnel
echo.
echo Na janela do Cloudflare, copie o link trycloudflare.com.
echo Envie o link, usuario e senha somente para operadores autorizados.
echo O menu "Painel Leon" fica dentro do painel web apos o login.
echo.
pause
"""


def backup_file(path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.backup_web_collab_{timestamp}")
    shutil.copy2(path, backup)
    return backup


def write_if_changed(path, content):
    normalized = content.replace("\n", os.linesep)
    if path.exists():
        current = path.read_text(encoding="utf-8", errors="replace")
        if current.replace("\r\n", "\n") == content.replace("\r\n", "\n"):
            print(f"Preservado sem alteração: {path.name}")
            return
        backup = backup_file(path)
        print(f"Backup criado: {backup.name}")
    path.write_text(normalized, encoding="utf-8")
    print(f"Criado: {path.name}")


def find_cloudflared():
    candidates = [
        TOOLS_DIR / "cloudflared.exe",
        Path(r"C:\Program Files\cloudflared\cloudflared.exe"),
    ]
    path_command = shutil.which("cloudflared")
    if path_command:
        candidates.append(Path(path_command))
    return next((path for path in candidates if path.exists()), None)


def main():
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    shortcuts = BASE_DIR / "ATALHOS_LEON" / "ACESSO_REMOTO"
    shortcuts.mkdir(parents=True, exist_ok=True)
    write_if_changed(shortcuts / "03_INICIAR_WEB.bat", WEB_BAT)
    write_if_changed(shortcuts / "04_INICIAR_TUNEL.bat", TUNNEL_BAT)
    write_if_changed(
        shortcuts / "02_INICIAR_WEB_E_TUNEL.bat",
        REMOTE_BAT,
    )

    cloudflared = find_cloudflared()
    if cloudflared:
        print(f"cloudflared encontrado em: {cloudflared}")
    else:
        print(
            "Baixe o cloudflared.exe no site oficial da Cloudflare e salve em "
            r"C:\XAU_ELITE_AI\tools\cloudflared.exe"
        )

    print("Acesso remoto preparado sem abrir portas no roteador.")
    print("O painel web agora inclui a visao do Painel Leon em modo leitura.")
    print(
        r"Execute: ATALHOS_LEON\ACESSO_REMOTO\02_INICIAR_WEB_E_TUNEL.bat"
    )


if __name__ == "__main__":
    main()
