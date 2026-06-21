import secrets
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
REQUIREMENTS_FILE = BASE_DIR / "requirements_web.txt"

DIRECTORIES = [
    BASE_DIR / "web_app" / "database",
    BASE_DIR / "web_app" / "routes",
    BASE_DIR / "web_app" / "services",
    BASE_DIR / "web_app" / "static" / "css",
    BASE_DIR / "web_app" / "static" / "uploads",
    BASE_DIR / "web_app" / "templates",
    BASE_DIR / "logs",
    BASE_DIR / "tools",
]


def _read_env_map():
    if not ENV_FILE.exists():
        return {}

    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _render_env(values):
    ordered_keys = [
        "WEB_HOST",
        "WEB_PORT",
        "MAX_UPLOAD_MB",
        "REMOTE_ACCESS_MODE",
        "SESSION_COOKIE_SECURE",
        "SECRET_KEY",
        "LEON_WEB_ADMIN_USERNAME",
        "LEON_WEB_ADMIN_PASSWORD",
        "TRADING_ECONOMICS_API_KEY",
    ]
    lines = [f"{key}={values[key]}" for key in ordered_keys if key in values]
    extra_keys = [key for key in values if key not in ordered_keys]
    lines.extend(f"{key}={values[key]}" for key in sorted(extra_keys))
    return "\n".join(lines) + "\n"


def create_directories():
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)


def create_env():
    existing = _read_env_map()
    created_new_file = not ENV_FILE.exists()

    values = {
        "WEB_HOST": existing.get("WEB_HOST", "127.0.0.1"),
        "WEB_PORT": existing.get("WEB_PORT", "5000"),
        "MAX_UPLOAD_MB": existing.get("MAX_UPLOAD_MB", "5"),
        "REMOTE_ACCESS_MODE": existing.get("REMOTE_ACCESS_MODE", "CLOUDFLARE_TUNNEL"),
        "SESSION_COOKIE_SECURE": existing.get("SESSION_COOKIE_SECURE", "false"),
        "SECRET_KEY": existing.get("SECRET_KEY", secrets.token_urlsafe(48)),
        "LEON_WEB_ADMIN_USERNAME": existing.get("LEON_WEB_ADMIN_USERNAME", "admin"),
        "LEON_WEB_ADMIN_PASSWORD": existing.get(
            "LEON_WEB_ADMIN_PASSWORD",
            secrets.token_urlsafe(18),
        ),
        "TRADING_ECONOMICS_API_KEY": existing.get("TRADING_ECONOMICS_API_KEY", ""),
    }

    ENV_FILE.write_text(_render_env(values), encoding="utf-8")

    return {
        "created_new_file": created_new_file,
        "password_was_created": "LEON_WEB_ADMIN_PASSWORD" not in existing,
        "admin_username": values["LEON_WEB_ADMIN_USERNAME"],
        "admin_password": values["LEON_WEB_ADMIN_PASSWORD"],
    }


def install_requirements():
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {REQUIREMENTS_FILE}")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(REQUIREMENTS_FILE),
        ],
        cwd=BASE_DIR,
    )


def initialize_database():
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from web_app.database.db import init_db

    init_db()


def main():
    print("Preparando LEON WEB COLLAB...")
    create_directories()
    env_info = create_env()
    install_requirements()
    initialize_database()

    print()
    print("========================================")
    print("LEON WEB COLLAB PRONTO")
    print(f"Painel: http://127.0.0.1:5000")
    print(f"Usuário inicial: {env_info['admin_username']}")

    if env_info["password_was_created"]:
        print(f"Senha inicial gerada: {env_info['admin_password']}")
    else:
        print("Senha inicial preservada no arquivo .env")

    print()
    print("Próximos comandos:")
    print("python setup_remote_access.py")
    print(
        r"ATALHOS_LEON\ACESSO_REMOTO\02_INICIAR_WEB_E_TUNEL.bat"
    )
    print()
    print("Boas práticas:")
    print("Troque a senha do admin depois do primeiro acesso.")
    print("Não compartilhe o link remoto publicamente.")
    print("O painel remoto é de supervisão e estudo, não de execução real.")
    print("========================================")


if __name__ == "__main__":
    main()
