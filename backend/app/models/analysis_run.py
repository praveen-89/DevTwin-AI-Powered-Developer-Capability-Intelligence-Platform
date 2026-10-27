"""
DevTwin Backend — AnalysisRun ORM Model
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

from sqlalchemy import UUID, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis_job import AnalysisJob
    from app.models.repository import Repository
    from app.models.observation import Observation


class AnalysisRun(Base):
    """
    Maps to the `analysis_runs` table.
    Represents a concrete, bounded execution attempt of an analysis_job.
    """

    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Text,
        default="QUEUED",
        nullable=False,
    )
    analyzer_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    error_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    analysis_job: Mapped["AnalysisJob"] = relationship(
        "AnalysisJob",
        back_populates="analysis_runs",
    )
    repository: Mapped["Repository"] = relationship(
        "Repository",
    )
    observations: Mapped[List["Observation"]] = relationship(
        "Observation",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnalysisRun id={self.id} analysis_job_id={self.analysis_job_id} status={self.status}>"

    # ------------------------------------------------------------------
    # Transient in-memory result slots (not persisted to DB).
    # These are assigned by the analysis runner between pipeline stages
    # so downstream stages can reference upstream results without extra
    # DB round-trips. __allow_unmapped__ tells SQLAlchemy's declarative
    # system to ignore these non-Mapped annotations.
    # ------------------------------------------------------------------
    __allow_unmapped__ = True

    _mining_result: Optional[Any] = None
    _skillgraph_result: Optional[Any] = None
    _coderisk_result: Optional[Any] = None
    _evidence_result: Optional[Any] = None
    _capability_result: Optional[Any] = None

