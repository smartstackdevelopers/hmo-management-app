"""S3-compatible private bucket adapter (AWS S3, MinIO, etc.)."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings


class S3CompatibleStorage:
    provider_name = "s3"

    def __init__(self, settings: Settings) -> None:
        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET is required when STORAGE_PROVIDER=s3")
        if not settings.s3_access_key_id or not settings.s3_secret_access_key:
            raise RuntimeError(
                "S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY are required for s3 provider"
            )
        try:
            import boto3
            from botocore.client import Config
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for S3 storage. Install apps/api requirements."
            ) from exc

        config_kwargs: dict[str, Any] = {"signature_version": "s3v4"}
        if settings.s3_force_path_style:
            config_kwargs["s3"] = {"addressing_style": "path"}

        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            config=Config(**config_kwargs),
        )

    def put_bytes(self, *, key: str, data: bytes, content_type: str) -> None:
        # Conditional put avoids silent overwrite when the bucket supports IfNoneMatch.
        # Fall back to head-check for broader S3-compatible compatibility.
        if self.exists(key=key):
            raise FileExistsError(f"Object already exists: {key}")
        # Do not set object ACL — private access is enforced by bucket policy
        # (Block Public Access). Some S3-compatible providers reject canned ACLs.
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def get_bytes(self, *, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 — map missing to KeyError
            raise KeyError(key) from exc
        return response["Body"].read()

    def delete(self, *, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def exists(self, *, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False
