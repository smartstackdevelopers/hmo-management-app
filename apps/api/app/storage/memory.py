"""In-process private store for unit tests and local runs without credentials."""

from __future__ import annotations


class InMemoryStorage:
    provider_name = "memory"

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    def put_bytes(self, *, key: str, data: bytes, content_type: str) -> None:
        if key in self._objects:
            raise FileExistsError(f"Object already exists: {key}")
        self._objects[key] = (data, content_type)

    def get_bytes(self, *, key: str) -> bytes:
        try:
            return self._objects[key][0]
        except KeyError as exc:
            raise KeyError(key) from exc

    def delete(self, *, key: str) -> None:
        self._objects.pop(key, None)

    def exists(self, *, key: str) -> bool:
        return key in self._objects

    def clear(self) -> None:
        self._objects.clear()
