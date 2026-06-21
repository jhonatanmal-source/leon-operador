import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_PATH = BASE_DIR / "web_app" / "database" / "leon_web.db"
ADMIN_BOOTSTRAP_FILE = BASE_DIR / "web_app" / "database" / "admin_bootstrap.json"
UPLOAD_FOLDER = BASE_DIR / "web_app" / "static" / "uploads"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
DEFAULT_ADMIN_USERNAME = (
    os.getenv("LEON_WEB_ADMIN_USERNAME", "admin").strip() or "admin"
)
DEFAULT_ADMIN_PASSWORD = os.getenv("LEON_WEB_ADMIN_PASSWORD", "").strip()
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
