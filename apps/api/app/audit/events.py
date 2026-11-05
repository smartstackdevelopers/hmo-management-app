"""Canonical audit action names."""

AUTH_SESSION_VALIDATED = "auth.session.validated"
AUTH_ACCESS_DENIED = "auth.access.denied"
AUTH_MFA_REQUIRED = "auth.mfa.required"
AUTH_TOKEN_INVALID = "auth.token.invalid"

ORG_CREATED = "organisation.create"
MEMBERSHIP_ASSIGNED = "membership.assign"
MEMBERSHIP_STATUS_CHANGED = "membership.status_change"

TENANT_CREATE = "tenant.create"
TENANT_UPDATE = "tenant.update"
TENANT_ARCHIVE = "tenant.archive"
PROPERTY_CREATE = "property.create"
PROPERTY_UPDATE = "property.update"
PROPERTY_ARCHIVE = "property.archive"
ROOM_CREATE = "room.create"
ROOM_UPDATE = "room.update"
ROOM_ARCHIVE = "room.archive"

EMERGENCY_REQUESTED = "emergency_access.requested"
EMERGENCY_APPROVED = "emergency_access.approved"
EMERGENCY_REJECTED = "emergency_access.rejected"
EMERGENCY_ACTIVATED = "emergency_access.activated"
EMERGENCY_EXPIRED = "emergency_access.expired"
EMERGENCY_REVOKED = "emergency_access.revoked"

AUDIT_READ = "audit.read"
