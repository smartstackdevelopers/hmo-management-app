"""F8.1 optional AI voice calling models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganisationVoiceCallingSettings(Base):
    __tablename__ = "organisation_voice_calling_settings"
    __table_args__ = (
        UniqueConstraint("organisation_id", name="uq_voice_calling_settings_org"),
        CheckConstraint(
            "provider_mode IN ('test', 'twilio', 'pending_approval')",
            name="ck_voice_calling_provider_mode",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="test")
    calling_hours: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    supported_languages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    voice_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    max_call_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    monthly_call_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_minutes_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consent_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recording_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    privacy_review_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    handover_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    provider_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VoiceCallSession(Base):
    __tablename__ = "voice_call_sessions"
    __table_args__ = (CheckConstraint("direction IN ('incoming', 'outgoing')", name="ck_voice_call_direction"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ringing")
    provider_call_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    caller_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    caller_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en-GB")
    consent_obtained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_disclosure_played: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    handover_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    handover_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    handover_assignee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    turns: Mapped[list["VoiceCallTurn"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class VoiceCallTurn(Base):
    __tablename__ = "voice_call_turns"
    __table_args__ = (UniqueConstraint("session_id", "turn_index", name="uq_voice_call_turn_session_idx"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voice_call_sessions.id", ondelete="CASCADE"), nullable=False
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    user_text_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    assistant_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    stt_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="test")
    tts_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="test")
    ai_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    handover_suggested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[VoiceCallSession] = relationship(back_populates="turns")
