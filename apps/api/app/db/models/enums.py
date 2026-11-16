"""Fixed core roles from the approved HMore proposal. Exactly six values."""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class HMoreRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ORGANISATION_ADMIN = "organisation_admin"
    LANDLORD = "landlord"
    TENANT = "tenant"
    SUPPORT_WORKER = "support_worker"
    MAINTENANCE_CONTRACTOR = "maintenance_contractor"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"


class AccountStatus(StrEnum):
    """User-level lifecycle for native HMore authentication (Prompt 12)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class RegistrationRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RecordStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


hmore_role_enum = SAEnum(
    HMoreRole,
    name="hmore_role",
    native_enum=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

membership_status_enum = SAEnum(
    MembershipStatus,
    name="membership_status",
    native_enum=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

account_status_enum = SAEnum(
    AccountStatus,
    name="account_status",
    native_enum=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

registration_request_status_enum = SAEnum(
    RegistrationRequestStatus,
    name="registration_request_status",
    native_enum=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

record_status_enum = SAEnum(
    RecordStatus,
    name="record_status",
    native_enum=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)
