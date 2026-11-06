"""SMTP email adapter — credentials from environment only."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger("hmore.communication.email")


class EmailAdapter:
    def send(self, *, to_email: str, subject: str, body_text: str) -> tuple[bool, str, str]:
        raise NotImplementedError


class SmtpEmailAdapter(EmailAdapter):
    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def send(self, *, to_email: str, subject: str, body_text: str) -> tuple[bool, str, str]:
        host = self._s.smtp_host
        port = self._s.smtp_port
        user = self._s.smtp_user
        password = self._s.smtp_password
        from_addr = self._s.smtp_from_email
        if not host or not from_addr:
            return False, "smtp_unconfigured", "SMTP_HOST or SMTP_FROM_EMAIL not configured — email not sent"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        try:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.starttls()
                if user and password:
                    smtp.login(user, password)
                smtp.sendmail(from_addr, [to_email], msg.as_string())
        except OSError as exc:
            logger.warning("smtp_send_failed to=%s err=%s", to_email, exc)
            return False, "smtp", str(exc)[:2000]
        # SMTP DATA success does not prove inbox delivery — status remains provider_accepted upstream.
        return True, "smtp", "Message accepted by SMTP server (delivery to recipient mailbox not confirmed)"


class TestEmailAdapter(EmailAdapter):
    """Test-only no-op — records intent without network."""

    def send(self, *, to_email: str, subject: str, body_text: str) -> tuple[bool, str, str]:
        return True, "test_email", f"Test adapter would send to {to_email} (not verified real delivery)"


def get_email_adapter(settings: Settings) -> EmailAdapter:
    if settings.email_adapter_mode == "smtp":
        return SmtpEmailAdapter(settings)
    return TestEmailAdapter()
