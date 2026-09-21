import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web_app import config
from web_app.app import create_app
from waitress import serve
app = create_app()
print(f"LEON Web Collab rodando em http://{config.WEB_HOST}:{config.WEB_PORT}")
serve(app, host=config.WEB_HOST, port=config.WEB_PORT)
