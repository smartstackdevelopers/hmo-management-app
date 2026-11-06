"""Notification delivery boundary for F2.2 reminders.

Real email / SMS / in-app providers belong to F2.12. This module defines a stable
interface so Celery workers can record delivery attempts without inventing a second
communications stack.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger("hmore.reminders")


@dataclass(frozen=True)
class ReminderMessage:
    organisation_id: str
    recipient_user_id: str
    subject: str
    body: str
    channel: str = "log"


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    provider: str
    detail: str


class NotificationProvider(Protocol):
    def send(self, message: ReminderMessage) -> DeliveryResult: ...


class LogNotificationProvider:
    """Development / Phase 2 foundation provider — logs only, no external send."""

    def send(self, message: ReminderMessage) -> DeliveryResult:
        logger.info(
            "reminder_delivery_stub org=%s recipient=%s channel=%s subject=%s",
            message.organisation_id,
            message.recipient_user_id,
            message.channel,
            message.subject,
        )
        return DeliveryResult(
            success=True,
            provider="log_stub",
            detail="Logged only — external delivery deferred to F2.12",
        )


def get_notification_provider() -> NotificationProvider:
    return LogNotificationProvider()
