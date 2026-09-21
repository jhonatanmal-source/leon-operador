from datetime import datetime

from flask import has_request_context, request

from web_app.config import BASE_DIR
from web_app.database.db import get_connection


LOG_FILE = BASE_DIR / "logs" / "web_access.log"


def log_action(action, user_id=None, username=None):
    now = datetime.now().isoformat(timespec="seconds")
    ip_address = request.remote_addr if has_request_context() else ""
    route = request.path if has_request_context() else ""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO access_logs (
                user_id, username, action, ip_address, route, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, username, action, ip_address, route, now),
        )

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(
            f"{now} | user_id={user_id or ''} | username={username or ''} "
            f"| ip={ip_address} | route={route} | action={action}\n"
        )
