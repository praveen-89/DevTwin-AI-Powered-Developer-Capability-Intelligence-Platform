"""
DevTwin Backend — Observation ORM Model
Maps to the `observations` table in Migration 001 (001_initial_schema.sql).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import UUID, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun
    from app.models.evidence import Evidence


class Observation(Base):
    """
    Directly detected, immutable facts produced by an analysis run.
    Observation ≠ Evidence. See DOMAIN_MODEL.md.
    """

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    source_tool: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    source_reference: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Numeric,
        nullable=True,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun",
        back_populates="observations",
    )
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="observation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Observation id={self.id} type={self.type} source_tool={self.source_tool}>"
