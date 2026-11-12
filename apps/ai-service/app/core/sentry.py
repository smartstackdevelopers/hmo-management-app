"""Optional Sentry for AI service."""

from __future__ import annotations

import os


def init_sentry() -> bool:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        return False

    environment = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
    traces_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_rate,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        send_default_pii=False,
    )
    return True
