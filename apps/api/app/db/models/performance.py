"""F7.4 performance benchmark persistence."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PerformanceBenchmarkRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "performance_benchmark_runs"
    __table_args__ = (Index("ix_perf_runs_started", "started_at"),)

    environment_label: Mapped[str] = mapped_column(String(64), nullable=False, default="ci")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sample_count_per_journey: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    concurrent_health_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PerformanceJourneyResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "performance_journey_results"
    __table_args__ = (Index("ix_perf_journey_run", "benchmark_run_id", "journey_key"),)

    benchmark_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("performance_benchmark_runs.id", ondelete="CASCADE"), nullable=False
    )
    journey_key: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(8), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p50_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p95_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p99_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status_codes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
