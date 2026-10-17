"""
DevTwin Backend — AnalysisJob ORM Model
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import UUID, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.analysis_run import AnalysisRun


class AnalysisJob(Base):
    """
    Maps to the `analysis_jobs` table.
    Represents a user/system request to analyze a repository.
    """

    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="analysis_jobs",
    )
    analysis_runs: Mapped[List["AnalysisRun"]] = relationship(
        "AnalysisRun",
        back_populates="analysis_job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnalysisJob id={self.id} repository_id={self.repository_id} status={self.status}>"
