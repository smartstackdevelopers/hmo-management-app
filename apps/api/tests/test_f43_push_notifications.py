"""F4.3 push notifications — unit tests with mocks. No provider credentials."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.communication.schemas import AnnouncementCreate
from app.core.config import Settings
from app.db.models.communication import CommunicationDelivery
from app.db.models.enums import HMoreRole, MembershipStatus
from app.db.models.push_devices import PushDeviceToken
from app.push.delivery import PUSH_BODY, deliver_push, enqueue_push_for_message
from app.push.expo_client import DATA_KEYS, EXPO_PUSH_URL
from app.push.schemas import PushDeviceRegister
from app.push.service import list_own_devices, register_device
from app.rbac.context import AuthorizationContext, MembershipView
from app.tenancy.context import OrganisationContext
from app.workers.celery_app import celery_app


def _ctx() -> OrganisationContext:
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    user = SimpleNamespace(
        id=user_id,
        authorization_version=1,
        external_subject="auth0|push",
        email="push@example.com",
        display_name="Push",
    )
    authz = AuthorizationContext(
        user=user,  # type: ignore[arg-type]
        memberships=[
            MembershipView(
                membership_id=uuid.uuid4(),
                role=HMoreRole.SUPPORT_WORKER,
                organisation_id=org_id,
                status=MembershipStatus.ACTIVE,
            )
        ],
        active_organisation_id=org_id,
        active_role=HMoreRole.SUPPORT_WORKER,
    )
    return OrganisationContext(
        user=user,  # type: ignore[arg-type]
        organisation_id=org_id,
        role=HMoreRole.SUPPORT_WORKER,
        authorization=authz,
    )


def _device(*, user_id: uuid.UUID, organisation_id: uuid.UUID, active: bool = True) -> PushDeviceToken:
    return PushDeviceToken(
        id=uuid.uuid4(),
        organisation_id=organisation_id,
        user_id=user_id,
        expo_push_token="ExponentPushToken[abcdefghij]",
        platform="ios",
        is_active=active,
        last_registered_at=datetime.now(timezone.utc),
    )


def _delivery(ctx: OrganisationContext) -> CommunicationDelivery:
    return CommunicationDelivery(
        id=uuid.uuid4(),
        organisation_id=ctx.organisation_id,
        target_type="communication_message",
        target_id=uuid.uuid4(),
        recipient_user_id=ctx.user_id,
        channel="push",
        status="queued",
        subject="HMore",
        body=PUSH_BODY,
        scheduled_at=datetime.now(timezone.utc),
        attempt_count=0,
        idempotency_key=f"push:message:{uuid.uuid4()}:{uuid.uuid4()}",
    )


def _routing_data() -> dict[str, str]:
    return {
        "message_id": str(uuid.uuid4()),
        "related_resource_type": "incident",
        "related_resource_id": str(uuid.uuid4()),
        "body": "Patient fracture narrative that must not be pushed",
    }


def test_register_token_binds_to_user() -> None:
    ctx = _ctx()
    session = MagicMock()
    session.scalar.return_value = None
    body = PushDeviceRegister(expo_push_token="ExponentPushToken[abcdefghij]", platform="android", device_name="Phone")
    out = register_device(session, ctx, body)
    row = session.add.call_args.args[0]
    assert isinstance(row, PushDeviceToken)
    assert row.user_id == ctx.user_id
    assert row.organisation_id == ctx.organisation_id
    assert row.is_active is True
    assert out["id"] == str(row.id)
    assert out["platform"] == "android"


def test_register_reactivates_own_disabled_token() -> None:
    ctx = _ctx()
    existing = _device(user_id=ctx.user_id, organisation_id=uuid.uuid4(), active=False)
    existing.disabled_reason = "DeviceNotRegistered"
    session = MagicMock()
    session.scalar.return_value = existing
    body = PushDeviceRegister(expo_push_token=existing.expo_push_token, platform="ios", app_version="1.2.0")
    out = register_device(session, ctx, body)
    assert existing.user_id == ctx.user_id
    assert existing.organisation_id == ctx.organisation_id
    assert existing.is_active is True
    assert existing.disabled_reason is None
    assert existing.app_version == "1.2.0"
    assert out["is_active"] is True
    session.add.assert_not_called()


def test_cannot_steal_another_users_token() -> None:
    ctx = _ctx()
    other_user = uuid.uuid4()
    existing = _device(user_id=other_user, organisation_id=ctx.organisation_id)
    session = MagicMock()
    session.scalar.return_value = existing
    body = PushDeviceRegister(expo_push_token=existing.expo_push_token, platform="ios")
    with pytest.raises(HTTPException) as exc:
        register_device(session, ctx, body)
    assert exc.value.status_code == 409
    session.add.assert_not_called()
    assert existing.user_id == other_user
    assert existing.is_active is True


def test_allow_push_false_skips_enqueue() -> None:
    ctx = _ctx()
    session = MagicMock()
    session.scalar.return_value = SimpleNamespace(allow_push=False)
    created = enqueue_push_for_message(
        session,
        organisation_id=ctx.organisation_id,
        recipient_user_id=ctx.user_id,
        message_id=uuid.uuid4(),
    )
    assert created == []
    session.add.assert_not_called()


def test_enqueue_uses_generic_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.push.delivery._schedule", lambda _delivery_id: None)
    ctx = _ctx()
    device = _device(user_id=ctx.user_id, organisation_id=ctx.organisation_id)
    session = MagicMock()
    session.scalar.side_effect = [SimpleNamespace(allow_push=True), None]
    session.scalars.return_value.all.return_value = [device]
    narrative = "Patient fracture narrative"
    enqueue_push_for_message(
        session,
        organisation_id=ctx.organisation_id,
        recipient_user_id=ctx.user_id,
        message_id=uuid.uuid4(),
    )
    added = session.add.call_args.args[0]
    assert added.channel == "push"
    assert added.status == "queued"
    assert added.body == PUSH_BODY
    assert narrative not in added.body
    assert narrative not in (added.subject or "")


def test_log_mode_does_not_mark_delivery_as_device_received() -> None:
    ctx = _ctx()
    delivery = _delivery(ctx)
    device = _device(user_id=ctx.user_id, organisation_id=ctx.organisation_id)
    http = MagicMock()
    settings = Settings(push_adapter_mode="log", expo_access_token="unit-test-token")
    result = deliver_push(
        MagicMock(),
        delivery,
        device,
        settings=settings,
        data=_routing_data(),
        http_post=http,
    )
    assert result["status"] == "failed"
    assert delivery.status == "failed"
    assert delivery.status != "sent"
    assert delivery.status != "delivered"
    assert "device_received" not in (delivery.last_error or "")
    assert "provider_not_configured" in (delivery.last_error or "")
    assert "not_sent_provider_unconfigured" in (delivery.last_error or "")
    http.assert_not_called()
    assert device.is_active is True

    missing_token = Settings(push_adapter_mode="expo", expo_access_token=None)
    delivery_two = _delivery(ctx)
    deliver_push(
        MagicMock(),
        delivery_two,
        device,
        settings=missing_token,
        data=_routing_data(),
        http_post=http,
    )
    assert delivery_two.status == "failed"
    assert "provider_not_configured" in (delivery_two.last_error or "")
    http.assert_not_called()


def test_invalid_ticket_deactivates_token() -> None:
    ctx = _ctx()
    delivery = _delivery(ctx)
    device = _device(user_id=ctx.user_id, organisation_id=ctx.organisation_id)
    seen: dict[str, object] = {}

    def http_post(url: str, payload: dict, headers: dict) -> dict:
        seen["url"] = url
        seen["payload"] = payload
        seen["authorization"] = headers.get("Authorization")
        return {
            "data": {
                "status": "error",
                "message": "not registered",
                "details": {"error": "DeviceNotRegistered"},
            }
        }

    settings = Settings(push_adapter_mode="expo", expo_access_token="unit-test-token")
    deliver_push(
        MagicMock(),
        delivery,
        device,
        settings=settings,
        data=_routing_data(),
        http_post=http_post,
    )
    payload = seen["payload"]
    assert isinstance(payload, dict)
    encoded = json.dumps(payload)
    assert seen["url"] == EXPO_PUSH_URL
    assert seen["authorization"] == "Bearer unit-test-token"
    assert payload["body"] == PUSH_BODY
    assert set(payload["data"]) == set(DATA_KEYS)
    assert "fracture" not in encoded
    assert delivery.status == "failed"
    assert delivery.status != "sent"
    assert device.is_active is False
    assert device.disabled_reason == "DeviceNotRegistered"


def test_ok_ticket_marks_sent_not_device_receipt() -> None:
    ctx = _ctx()
    delivery = _delivery(ctx)
    device = _device(user_id=ctx.user_id, organisation_id=ctx.organisation_id)

    def http_post(url: str, payload: dict, headers: dict) -> dict:
        return {"data": {"status": "ok", "id": "ticket-ok-1"}}

    settings = Settings(push_adapter_mode="expo", expo_access_token="unit-test-token")
    deliver_push(
        MagicMock(),
        delivery,
        device,
        settings=settings,
        data=_routing_data(),
        http_post=http_post,
    )
    assert delivery.status == "sent"
    assert delivery.provider_message_id == "ticket-ok-1"
    assert delivery.provider_name == "expo"
    assert delivery.last_error is None
    assert delivery.status != "delivered"
    assert device.is_active is True

    http = MagicMock()
    again = deliver_push(
        MagicMock(),
        delivery,
        device,
        settings=settings,
        data=_routing_data(),
        http_post=http,
    )
    assert again["noop"] is True
    http.assert_not_called()


def test_list_devices_is_scoped_to_caller_org_and_user() -> None:
    ctx = _ctx()
    other_org = uuid.uuid4()
    other_user = uuid.uuid4()
    session = MagicMock()
    session.scalars.return_value.all.return_value = []
    assert list_own_devices(session, ctx) == []
    statement = session.scalars.call_args.args[0]
    values = list(statement.compile().params.values())
    assert ctx.organisation_id in values
    assert ctx.user_id in values
    assert other_org not in values
    assert other_user not in values


def test_announcement_channels_allow_push() -> None:
    created = AnnouncementCreate(
        title="Water",
        body="The tank is being cleaned tomorrow.",
        audience="tenants_only",
        channels={"push": True},
    )
    assert created.channels["push"] is True
    with pytest.raises(ValidationError):
        AnnouncementCreate(
            title="Water",
            body="The tank is being cleaned tomorrow.",
            audience="tenants_only",
            channels={"pigeon": True},
        )


def test_push_celery_tasks_are_scheduled() -> None:
    assert "hmore.push.dispatch_delivery" in celery_app.tasks
    assert "hmore.push.dispatch_pending" in celery_app.tasks
    entry = celery_app.conf.beat_schedule["dispatch-pending-push-every-45-seconds"]
    assert entry["task"] == "hmore.push.dispatch_pending"
    assert 30 <= float(entry["schedule"]) <= 60

