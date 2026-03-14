import os
import re
from datetime import datetime


def _sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", filename or "document.pdf")
    return sanitized.strip("._") or "document.pdf"


def build_storage_name(filename: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{timestamp}_{_sanitize_filename(filename)}"


def save_file_bytes(data: bytes, folder: str, filename: str) -> str:
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)

    with open(file_path, "wb") as f:
        f.write(data)

    return file_path


def save_file(file, folder):
    return save_file_bytes(file.file.read(), folder, build_storage_name(file.filename))
