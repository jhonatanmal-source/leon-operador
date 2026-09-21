from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename

from web_app.config import ALLOWED_EXTENSIONS, UPLOAD_FOLDER


def allowed_file(filename):
    name = str(filename or "")
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file):
    if file is None or not file.filename:
        return None
    if not allowed_file(file.filename):
        raise ValueError("Formato inválido. Envie somente JPG, JPEG ou PNG.")

    safe_name = secure_filename(file.filename)
    suffix = Path(safe_name).suffix.lower()
    header = file.stream.read(12)
    file.stream.seek(0)
    is_jpeg = header.startswith(b"\xff\xd8\xff")
    is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"} and not is_jpeg:
        raise ValueError("O conteúdo do arquivo não é uma imagem JPEG válida.")
    if suffix == ".png" and not is_png:
        raise ValueError("O conteúdo do arquivo não é uma imagem PNG válida.")

    stem = Path(safe_name).stem[:80] or "analise"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    stored_name = f"{timestamp}_{stem}{suffix}"

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    file.save(UPLOAD_FOLDER / stored_name)
    return stored_name
