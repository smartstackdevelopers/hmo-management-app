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

record_status_enum = SAEnum(
    RecordStatus,
    name="record_status",
    native_enum=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)
