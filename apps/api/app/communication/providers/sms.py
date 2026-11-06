"""SMS adapter — Twilio when configured; test stub otherwise."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger("hmore.communication.sms")


class SmsAdapter:
    def send(self, *, to_number: str, body: str) -> tuple[bool, str, str]:
        raise NotImplementedError


class TwilioSmsAdapter(SmsAdapter):
    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def send(self, *, to_number: str, body: str) -> tuple[bool, str, str]:
        account = self._s.twilio_account_sid
        token = self._s.twilio_auth_token
        from_num = self._s.twilio_from_number
        if not account or not token or not from_num:
            return False, "twilio_unconfigured", "Twilio credentials incomplete — SMS not sent"
        try:
            from twilio.rest import Client  # type: ignore[import-untyped]

            client = Client(account, token)
            message = client.messages.create(body=body[:1600], from_=from_num, to=to_number)
        except Exception as exc:  # noqa: BLE001
            logger.warning("twilio_send_failed to=%s err=%s", to_number, exc)
            return False, "twilio", str(exc)[:2000]
        return True, "twilio", f"sid={message.sid} (handset delivery not confirmed)"


class TestSmsAdapter(SmsAdapter):
    def send(self, *, to_number: str, body: str) -> tuple[bool, str, str]:
        return True, "test_sms", f"Test adapter would SMS {to_number} (not verified real delivery)"


def get_sms_adapter(settings: Settings) -> SmsAdapter:
    if settings.sms_adapter_mode == "twilio":
        return TwilioSmsAdapter(settings)
    return TestSmsAdapter()
