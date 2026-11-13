"""F8.6 digital ID and e-signatures access."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.db.models.digital_id_esign import DigitalIdentityRecord, EsignSigner, EsignSigningRequest
from app.db.models.enums import HMoreRole
from app.rbac.permissions import Permission
from app.rbac.service import require_permission
from app.tenancy.context import OrganisationContext


def require_read(ctx: OrganisationContext) -> None:
    if ctx.role == HMoreRole.SUPER_ADMIN:
        return
    require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_READ)


def assert_signer_may_sign(ctx: OrganisationContext, signer: EsignSigner, request: EsignSigningRequest) -> None:
    if request.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Signing request not found")
    if signer.signer_user_id != ctx.user_id and ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_SIGN)
        if signer.signer_user_id != ctx.user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not an assigned signer")


def assert_identity_owner(ctx: OrganisationContext, record: DigitalIdentityRecord) -> None:
    if record.organisation_id != ctx.organisation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Identity record not found")
    if record.user_id != ctx.user_id and ctx.role != HMoreRole.SUPER_ADMIN:
        require_permission(ctx.authorization, Permission.DIGITAL_ID_ESIGN_IDENTITY_VERIFY)
