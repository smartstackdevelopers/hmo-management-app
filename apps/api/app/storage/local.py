"""Local filesystem private store for development. Not publicly HTTP-served."""

from __future__ import annotations

from pathlib import Path


class LocalDiskStorage:
    provider_name = "local"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        # Reject path traversal — keys are relative posix-style segments only.
        if ".." in key.split("/") or key.startswith(("/", "\\")):
            raise ValueError("Invalid storage key")
        path = (self.root / key).resolve()
        if not str(path).startswith(str(self.root)):
            raise ValueError("Invalid storage key")
        return path

    def put_bytes(self, *, key: str, data: bytes, content_type: str) -> None:
        path = self._path_for(key)
        if path.exists():
            raise FileExistsError(f"Object already exists: {key}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        # content_type retained in DB metadata only for local backend

    def get_bytes(self, *, key: str) -> bytes:
        path = self._path_for(key)
        if not path.is_file():
            raise KeyError(key)
        return path.read_bytes()

    def delete(self, *, key: str) -> None:
        path = self._path_for(key)
        if path.is_file():
            path.unlink()

    def exists(self, *, key: str) -> bool:
        return self._path_for(key).is_file()
