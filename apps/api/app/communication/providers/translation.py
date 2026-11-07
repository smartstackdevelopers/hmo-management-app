"""Translation provider abstraction — test stub unless a real API is configured."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


class TranslationAdapter:
    def translate(self, *, text: str, source_language: str, target_language: str) -> tuple[bool, str, str, str | None]:
        """Return (ok, provider, message, translated_or_none)."""


class TestTranslationAdapter(TranslationAdapter):
    def translate(self, *, text: str, source_language: str, target_language: str) -> tuple[bool, str, str, str | None]:
        return (
            True,
            "test_translate",
            "Echo translation (not verified with a real provider)",
            f"[{target_language}] {text}",
        )


def get_translation_adapter(settings: Settings) -> TranslationAdapter:
    return TestTranslationAdapter()
