"""
DevTwin Backend — Capability ORM Models
Maps to `developer_capabilities`, `capability_history`, and `skill_gaps` tables
in Migration 001 (001_initial_schema.sql).
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun
    from app.models.developer import Developer
    from app.models.taxonomy import Concept, Skill, Technology


class DeveloperCapability(Base):
    """
    Current capability state per developer per target.
    Uses Exclusive Arc (ADR-005): exactly one target FK (skill_id, technology_id, concept_id) is populated.
    """

    __tablename__ = "developer_capabilities"
    __table_args__ = (
        CheckConstraint(
            "score BETWEEN 0 AND 1",
            name="chk_developer_capability_score",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="chk_developer_capability_confidence",
        ),
        CheckConstraint(
            "num_nonnulls(skill_id, technology_id, concept_id) = 1",
            name="capability_target_exclusive_arc",
        ),
        UniqueConstraint(
            "developer_id",
            "skill_id",
            "technology_id",
            "concept_id",
            name="capability_unique_target",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    developer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Exclusive Arc (ADR-005)
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=True,
    )
    technology_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technologies.id", ondelete="CASCADE"),
        nullable=True,
    )
    concept_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=True,
    )

    score: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    scoring_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    developer: Mapped["Developer"] = relationship("Developer")
    skill: Mapped[Optional["Skill"]] = relationship("Skill")
    technology: Mapped[Optional["Technology"]] = relationship("Technology")
    concept: Mapped[Optional["Concept"]] = relationship("Concept")

    history: Mapped[List["CapabilityHistory"]] = relationship(
        "CapabilityHistory",
        back_populates="capability",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        target = f"skill={self.skill_id}" if self.skill_id else (f"tech={self.technology_id}" if self.technology_id else f"concept={self.concept_id}")
        return f"<DeveloperCapability id={self.id} dev={self.developer_id} {target} score={self.score} conf={self.confidence}>"


class CapabilityHistory(Base):
    """
    Append-only history of capability states (ADR-004).
    Never overwrite or delete rows; represents chronological progression.
    """

    __tablename__ = "capability_history"
    __table_args__ = (
        CheckConstraint(
            "score BETWEEN 0 AND 1",
            name="chk_capability_history_score",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="chk_capability_history_confidence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developer_capabilities.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    score: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    scoring_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    capability: Mapped["DeveloperCapability"] = relationship(
        "DeveloperCapability",
        back_populates="history",
    )
    analysis_run: Mapped[Optional["AnalysisRun"]] = relationship("AnalysisRun")

    def __repr__(self) -> str:
        return f"<CapabilityHistory id={self.id} cap_id={self.capability_id} score={self.score} conf={self.confidence}>"


class SkillGap(Base):
    """
    Delta between required capability target and current developer capability.
    Uses Exclusive Arc same as developer_capabilities.
    """

    __tablename__ = "skill_gaps"
    __table_args__ = (
        CheckConstraint(
            "target_score BETWEEN 0 AND 1",
            name="chk_skill_gap_target_score",
        ),
        CheckConstraint(
            "current_score BETWEEN 0 AND 1",
            name="chk_skill_gap_current_score",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 1",
            name="chk_skill_gap_confidence",
        ),
        CheckConstraint(
            "num_nonnulls(target_skill_id, target_technology_id, target_concept_id) = 1",
            name="skill_gap_target_exclusive_arc",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    developer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Exclusive Arc
    target_skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_technology_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technologies.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_concept_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=True,
    )

    target_score: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    current_score: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    gap_value: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    developer: Mapped["Developer"] = relationship("Developer")
    target_skill: Mapped[Optional["Skill"]] = relationship("Skill")
    target_technology: Mapped[Optional["Technology"]] = relationship("Technology")
    target_concept: Mapped[Optional["Concept"]] = relationship("Concept")

    def __repr__(self) -> str:
        return f"<SkillGap id={self.id} dev={self.developer_id} gap={self.gap_value} conf={self.confidence}>"
