"""Unit tests for the F1.4 role registry and permission matrix (no identity provider)."""

from __future__ import annotations

import pytest

from app.db.models.enums import HMoreRole
from app.rbac.matrix import ROLE_PERMISSIONS, role_has_permission
from app.rbac.permissions import PERMISSION_CATALOG, Permission, parse_permission
from app.rbac.roles import APPROVED_ROLE_COUNT, ROLE_DEFINITIONS, parse_role


def test_exactly_six_approved_roles() -> None:
    assert len(HMoreRole) == APPROVED_ROLE_COUNT == 6
    assert set(ROLE_DEFINITIONS) == set(HMoreRole)
    names = {definition.display_name for definition in ROLE_DEFINITIONS.values()}
    assert names == {
        "Super Admin",
        "Organisation Admin",
        "Landlord",
        "Tenant",
        "Support Worker",
        "Maintenance & Contractors",
    }


def test_no_removed_core_roles() -> None:
    forbidden = {
        "council_officer",
        "housing_manager",
        "compliance_officer",
        "finance_officer",
        "facilities_manager",
        "auditor",
    }
    values = {role.value for role in HMoreRole}
    assert values.isdisjoint(forbidden)


def test_unknown_role_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown role"):
        parse_role("council_officer")


def test_permission_catalog_complete() -> None:
    assert set(PERMISSION_CATALOG) == set(Permission)
    for meta in PERMISSION_CATALOG.values():
        assert meta.purpose.strip()


def test_matrix_covers_every_role() -> None:
    assert set(ROLE_PERMISSIONS) == set(HMoreRole)
    for role, perms in ROLE_PERMISSIONS.items():
        assert len(perms) > 0, role
        for permission in perms:
            assert permission in PERMISSION_CATALOG


def test_deny_by_default_unmapped_permission() -> None:
    assert not role_has_permission(HMoreRole.TENANT, Permission.ORGANISATIONS_MANAGE)
    assert not role_has_permission(HMoreRole.LANDLORD, Permission.AUDIT_LOGS_READ)
    assert not role_has_permission(
        HMoreRole.MAINTENANCE_CONTRACTOR, Permission.ROLE_ASSIGNMENTS_MANAGE
    )


def test_explicit_allows() -> None:
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.ORGANISATIONS_CREATE)
    assert role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.AUDIT_LOGS_READ)
    assert role_has_permission(HMoreRole.LANDLORD, Permission.PROPERTIES_MANAGE)
    assert role_has_permission(HMoreRole.TENANT, Permission.REPAIRS_CREATE_OWN)
    assert role_has_permission(
        HMoreRole.SUPPORT_WORKER, Permission.SUPPORT_NOTES_CREATE_ASSIGNED
    )
    assert role_has_permission(
        HMoreRole.MAINTENANCE_CONTRACTOR, Permission.WORK_ORDERS_UPDATE_ASSIGNED
    )


def test_no_wildcard_permission_identifier() -> None:
    for permission in Permission:
        assert "*" not in permission.value
        assert permission.value == permission.value.lower()


def test_unknown_permission_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown permission"):
        parse_permission("everything.*")

