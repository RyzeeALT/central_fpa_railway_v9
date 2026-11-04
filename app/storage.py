import os
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}


def _validate(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    original = secure_filename(file_storage.filename)
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Formato não permitido. Use PNG, JPG, JPEG ou WEBP.")
    if file_storage.mimetype and file_storage.mimetype.lower() not in ALLOWED_IMAGE_MIMES:
        raise ValueError("O arquivo enviado não parece ser uma imagem válida.")
    return original, suffix


def railway_volume_root():
    mount = (os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or "").strip()
    return Path(mount) if mount else None


def storage_backend():
    return "railway-volume" if railway_volume_root() else "local"


def upload_root():
    root = railway_volume_root()
    if root:
        return root / "uploads" / "tools"
    return Path(current_app.static_folder) / "uploads" / "tools"


def save_tool_image(file_storage):
    validated = _validate(file_storage)
    if not validated:
        return ""
    _original, suffix = validated
    folder = upload_root()
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    file_storage.save(folder / filename)
    if storage_backend() == "railway-volume":
        return f"/media/tools/{filename}"
    return f"/static/uploads/tools/{filename}"


def stored_image_path(image_url):
    if not image_url:
        return None
    if image_url.startswith("/media/tools/"):
        root = railway_volume_root()
        if not root:
            return None
        return root / "uploads" / "tools" / image_url.rsplit("/", 1)[-1]
    if image_url.startswith("/static/uploads/tools/"):
        return Path(current_app.static_folder) / "uploads" / "tools" / image_url.rsplit("/", 1)[-1]
    return None


def delete_stored_image(image_url):
    path = stored_image_path(image_url)
    if not path:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
