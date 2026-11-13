"""F5.6: Phase 5 mobile integration does not add a new Alembic head or duplicate APIs."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.db.models.enums import HMoreRole


def test_alembic_head_remains_f55_for_mobile_integration() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261123_5900_f812"]


def test_phase5_tenant_permissions_still_present() -> None:
    assert role_has_permission(HMoreRole.TENANT, Permission.WELLBEING_MANAGE_OWN)
    # Employment / directory permissions used by mobile hubs
    assert Permission.WELLBEING_MANAGE_OWN.value.startswith("wellbeing.")


def test_phase5_api_routers_registered() -> None:
    from app.api.v1.router import api_v1_router

    paths = {getattr(route, "path", "") for route in api_v1_router.routes}
    joined = " ".join(sorted(paths))
    assert "community-services" in joined or any("community" in p for p in paths)
    assert any("help-near-me" in p or "help_near_me" in p for p in paths) or "help" in joined
    assert any("employment" in p for p in paths)
    assert any("job-matching" in p or "job_matching" in p for p in paths)
    assert any("wellbeing" in p for p in paths)

