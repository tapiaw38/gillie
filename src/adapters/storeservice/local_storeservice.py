import os
import mimetypes
from pathlib import Path
from typing import BinaryIO


class LocalStoreService:
    """Stores files on the local filesystem and serves them via a static URL."""

    def __init__(self, base_path: str, base_url: str):
        self.base_path = Path(base_path)
        self.base_url = base_url.rstrip("/")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def put_object(
        self, file: BinaryIO, user_file: str, filename: str, size: int, object_id: str
    ) -> str:
        name, ext = os.path.splitext(filename)
        relative_path = f"files/{user_file}/{name}{object_id}{ext}"
        full_path = self.base_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        buffer = file.read()
        with open(full_path, "wb") as f:
            f.write(buffer)

        return relative_path

    def generate_url(self, key_name: str) -> str:
        return f"{self.base_url}/{key_name}"

    def delete_object(self, key_name: str) -> None:
        full_path = self.base_path / key_name
        if full_path.exists():
            full_path.unlink()

    def get_object(self, key_name: str) -> bytes:
        full_path = self.base_path / key_name
        with open(full_path, "rb") as f:
            return f.read()
