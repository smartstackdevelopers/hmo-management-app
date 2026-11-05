"""F1.8 private file storage tests.

Unit tests use the in-memory backend (mocked storage). PostgreSQL-marked tests
require DATABASE_URL. Real S3/MinIO integration is opt-in via STORAGE_PROVIDER=s3
and is not claimed as passed when skipped.
"""

from __future__ import annotations

import io
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.models.enums import HMoreRole, MembershipStatus
from app.main import app
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.storage.keys import build_object_key, normalize_filename
from app.storage.memory import InMemoryStorage
from app.storage.validation import validate_upload
from app.tenancy.context import OrganisationContext


def test_files_permissions_matrix() -> None:
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.FILES_MANAGE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.FILES_READ)
    assert not role_has_permission(HMoreRole.TENANT, Permission.FILES_MANAGE)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.FILES_READ)


def test_normalize_filename_blocks_traversal() -> None:
    assert normalize_filename("../../etc/passwd") == "passwd"
    assert normalize_filename("a\\b\\c.pdf") == "c.pdf"
    assert ".." not in normalize_filename("../x.pdf")


def test_object_key_is_random_and_org_scoped() -> None:
    org = uuid.uuid4()
    key_a = build_object_key(organisation_id=org, original_filename="report.pdf")
    key_b = build_object_key(organisation_id=org, original_filename="report.pdf")
    assert key_a != key_b
    assert key_a.startswith(f"org/{org}/")
    assert key_a.endswith(".pdf")
    assert "report" not in key_a


def test_validate_rejects_disallowed_type_and_oversize() -> None:
    settings = Settings(
        storage_max_upload_bytes=100,
        storage_allowed_content_types="application/pdf,image/png",
    )
    with pytest.raises(HTTPException) as oversized:
        validate_upload(
            settings=settings,
            filename="big.pdf",
            declared_content_type="application/pdf",
            data=b"%PDF" + b"x" * 200,
        )
    assert oversized.value.status_code == 413

    with pytest.raises(HTTPException) as bad_type:
        validate_upload(
            settings=settings,
            filename="x.bin",
            declared_content_type="application/octet-stream",
            data=b"\x00\x01\x02\x03",
        )
    assert bad_type.value.status_code == 400


def test_validate_accepts_pdf_by_signature() -> None:
    settings = Settings(storage_allowed_content_types="application/pdf")
    result = validate_upload(
        settings=settings,
        filename="note.txt",
        declared_content_type="text/plain",
        data=b"%PDF-1.4 fake",
    )
    assert result.content_type == "application/pdf"


def test_memory_backend_put_get_delete_no_overwrite() -> None:
    store = InMemoryStorage()
    store.put_bytes(key="a", data=b"hello", content_type="text/plain")
    assert store.get_bytes(key="a") == b"hello"
    with pytest.raises(FileExistsError):
        store.put_bytes(key="a", data=b"other", content_type="text/plain")
    store.delete(key="a")
    assert not store.exists(key="a")


def test_unauthenticated_files_api_returns_401() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/files").status_code == 401
    assert client.post("/api/v1/files", files={"upload": ("a.pdf", b"%PDF", "application/pdf")}).status_code == 401


def _org_ctx(role: HMoreRole, org_id: uuid.UUID | None = None) -> OrganisationContext:
    organisation_id = org_id or uuid.uuid4()
    user = SimpleNamespace(
        id=uuid.uuid4(),
        authorization_version=1,
        external_subject=f"auth0|{uuid.uuid4()}",
        email="u@example.com",
        display_name="U",
    )
    authz = AuthorizationContext(
        user=user,  # type: ignore[arg-type]
        memberships=[
            MembershipView(
                membership_id=uuid.uuid4(),
                role=role,
                organisation_id=organisation_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=organisation_id,
        active_role=role,
    )
    return OrganisationContext(
        user=user,  # type: ignore[arg-type]
        organisation_id=organisation_id,
        role=role,
        authorization=authz,
    )


@pytest.mark.postgres
def test_upload_download_delete_and_cross_org_denial(db_session, unique_suffix: str) -> None:
    from app.db.models import Organisation, OrganisationMembership, User
    from app.storage.memory import InMemoryStorage
    from app.storage import service as file_service
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

    apply_platform_rls_bypass(db_session)
    org_a = Organisation(name="FA", slug=f"fa-{unique_suffix}")
    org_b = Organisation(name="FB", slug=f"fb-{unique_suffix}")
    user_a = User(
        email=f"fa-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    user_b = User(
        email=f"fb-{unique_suffix}@example.com",
        display_name="B",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org_a, org_b, user_a, user_b])
    db_session.flush()
    db_session.add_all(
        [
            OrganisationMembership(
                user_id=user_a.id,
                organisation_id=org_a.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
            OrganisationMembership(
                user_id=user_b.id,
                organisation_id=org_b.id,
                role=HMoreRole.ORGANISATION_ADMIN,
                status=MembershipStatus.ACTIVE,
            ),
        ]
    )
    db_session.flush()

    backend = InMemoryStorage()
    settings = Settings(
        storage_provider="memory",
        storage_allowed_content_types="application/pdf",
        storage_max_upload_bytes=1_000_000,
    )
    ctx_a = _org_ctx(HMoreRole.ORGANISATION_ADMIN, org_a.id)
    ctx_a.user.id = user_a.id  # type: ignore[attr-defined]
    ctx_a.authorization.user.id = user_a.id  # type: ignore[attr-defined]
    ctx_b = _org_ctx(HMoreRole.ORGANISATION_ADMIN, org_b.id)
    ctx_b.user.id = user_b.id  # type: ignore[attr-defined]
    ctx_b.authorization.user.id = user_b.id  # type: ignore[attr-defined]

    apply_organisation_rls(db_session, org_a.id)
    meta = file_service.upload_file(
        db_session,
        ctx_a,
        filename="lease.pdf",
        declared_content_type="application/pdf",
        data=b"%PDF-1.4 test",
        settings=settings,
        backend=backend,
    )
    assert meta["status"] == "active"
    assert "storage_key" not in meta
    file_id = uuid.UUID(meta["id"])

    row, payload = file_service.download_file(
        db_session, ctx_a, file_id, backend=backend
    )
    assert payload.startswith(b"%PDF")
    assert row.checksum_sha256

    apply_organisation_rls(db_session, org_b.id)
    with pytest.raises(HTTPException) as denied:
        file_service.download_file(db_session, ctx_b, file_id, backend=backend)
    assert denied.value.status_code in {403, 404}

    apply_organisation_rls(db_session, org_a.id)
    deleted = file_service.delete_file(db_session, ctx_a, file_id, backend=backend)
    assert deleted["status"] == "deleted"
    with pytest.raises(HTTPException):
        file_service.download_file(db_session, ctx_a, file_id, backend=backend)


@pytest.mark.postgres
def test_upload_persists_audit_event(db_session, unique_suffix: str) -> None:
    from app.audit.events import FILE_UPLOAD
    from app.db.models import Organisation, User
    from app.db.models.audit import AuditEvent
    from app.storage.memory import InMemoryStorage
    from app.storage import service as file_service
    from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass
    from sqlalchemy import select

    apply_platform_rls_bypass(db_session)
    org = Organisation(name="AuditFile", slug=f"af-{unique_suffix}")
    user = User(
        email=f"af-{unique_suffix}@example.com",
        display_name="A",
        external_subject=f"auth0|{uuid.uuid4()}",
    )
    db_session.add_all([org, user])
    db_session.flush()
    ctx = _org_ctx(HMoreRole.ORGANISATION_ADMIN, org.id)
    ctx.user.id = user.id  # type: ignore[attr-defined]
    ctx.authorization.user.id = user.id  # type: ignore[attr-defined]
    apply_organisation_rls(db_session, org.id)
    file_service.upload_file(
        db_session,
        ctx,
        filename="a.pdf",
        declared_content_type="application/pdf",
        data=b"%PDF-1.4",
        settings=Settings(storage_allowed_content_types="application/pdf"),
        backend=InMemoryStorage(),
    )
    events = list(
        db_session.scalars(select(AuditEvent).where(AuditEvent.action == FILE_UPLOAD))
    )
    assert len(events) >= 1
    assert events[-1].organisation_id == org.id
    assert events[-1].actor_user_id == user.id
