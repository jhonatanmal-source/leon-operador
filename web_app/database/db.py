import sqlite3
import json
import secrets
from datetime import datetime

from werkzeug.security import generate_password_hash

from web_app.config import (
    ADMIN_BOOTSTRAP_FILE,
    DATABASE_PATH,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
)


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        DATABASE_PATH,
        factory=ClosingConnection,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                must_change_password INTEGER DEFAULT 1,
                created_at TEXT,
                last_login TEXT
            );

            CREATE TABLE IF NOT EXISTS human_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT DEFAULT 'XAUUSD',
                timeframe TEXT NOT NULL,
                direction TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                text_analysis TEXT NOT NULL,
                image_path TEXT,
                status TEXT DEFAULT 'PENDENTE',
                supervisor_comment TEXT,
                quality_score INTEGER DEFAULT 0,
                created_at TEXT,
                reviewed_at TEXT,
                reviewed_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (reviewed_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS leon_understanding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER NOT NULL,
                leon_summary TEXT NOT NULL,
                detected_keywords TEXT,
                confidence_score INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (analysis_id) REFERENCES human_analyses(id)
            );

            CREATE TABLE IF NOT EXISTS operator_reputation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                total_analyses INTEGER DEFAULT 0,
                approved_analyses INTEGER DEFAULT 0,
                rejected_analyses INTEGER DEFAULT 0,
                average_quality INTEGER DEFAULT 0,
                confidence_level TEXT DEFAULT 'BAIXA',
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT NOT NULL,
                ip_address TEXT,
                route TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_user
                ON human_analyses(user_id);
            CREATE INDEX IF NOT EXISTS idx_analyses_status
                ON human_analyses(status);
            CREATE INDEX IF NOT EXISTS idx_access_logs_created
                ON access_logs(created_at);
            """
        )
    create_default_admin()


def _bootstrap_admin_credentials():
    username = DEFAULT_ADMIN_USERNAME
    if DEFAULT_ADMIN_PASSWORD:
        return username, DEFAULT_ADMIN_PASSWORD

    if ADMIN_BOOTSTRAP_FILE.exists():
        try:
            data = json.loads(ADMIN_BOOTSTRAP_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}

        stored_username = str(data.get("username", "")).strip() or username
        stored_password = str(data.get("password", "")).strip()
        if stored_password:
            return stored_username, stored_password

    generated_password = secrets.token_urlsafe(18)
    ADMIN_BOOTSTRAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADMIN_BOOTSTRAP_FILE.write_text(
        json.dumps(
            {
                "username": username,
                "password": generated_password,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return username, generated_password


def create_default_admin():
    now = datetime.now().isoformat(timespec="seconds")
    username, password = _bootstrap_admin_credentials()
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing:
            return existing["id"]

        cursor = connection.execute(
            """
            INSERT INTO users (
                username, password_hash, role, is_active,
                must_change_password, created_at
            )
            VALUES (?, ?, 'ADMIN', 1, 1, ?)
            """,
            (
                username,
                generate_password_hash(password),
                now,
            ),
        )
        user_id = cursor.lastrowid
        connection.execute(
            """
            INSERT OR IGNORE INTO operator_reputation (
                user_id, updated_at
            )
            VALUES (?, ?)
            """,
            (user_id, now),
        )
        return user_id
