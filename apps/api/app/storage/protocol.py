"""Storage backend protocol. Application code depends on this, not a vendor SDK."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Private object storage operations. Buckets/containers must not be public."""

    @property
    def provider_name(self) -> str: ...

    def put_bytes(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Store object bytes at key. Must not overwrite silently if backend supports."""
        ...

    def get_bytes(self, *, key: str) -> bytes:
        """Return object bytes. Raises KeyError if missing."""
        ...

    def delete(self, *, key: str) -> None:
        """Delete object if present. Missing keys are not an error."""
        ...

    def exists(self, *, key: str) -> bool: ...
