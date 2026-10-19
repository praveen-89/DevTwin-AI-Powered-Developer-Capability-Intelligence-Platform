"""
DevTwin Backend — RiskFinding ORM Model
Maps to the `risk_findings` table in Migration 001 (001_initial_schema.sql).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import UUID, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun
    from app.models.observation import Observation
    from app.models.repository import Repository


class RiskFinding(Base):
    """
    CodeRisk signals. Risk ≠ Competence — see DOMAIN_MODEL.md and RULES.md.
    commit_id is nullable; only set when Git history attributes the risk to a specific commit.
    """

    __tablename__ = "risk_findings"
    __table_args__ = (
        CheckConstraint(
            "category IN ('SECURITY', 'RELIABILITY', 'TESTING', 'MAINTAINABILITY', 'DEPENDENCY', 'ARCHITECTURE')",
            name="chk_risk_findings_category",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_risk_findings_severity",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="chk_risk_findings_confidence",
        ),
    )

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
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("observations.id", ondelete="CASCADE"),
        nullable=False,
    )
    commit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commits.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    risk_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    line_start: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    line_end: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    repository: Mapped["Repository"] = relationship(
        "Repository",
    )
    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun",
    )
    observation: Mapped["Observation"] = relationship(
        "Observation",
    )

    def __repr__(self) -> str:
        return f"<RiskFinding id={self.id} risk_type={self.risk_type} severity={self.severity} category={self.category}>"
