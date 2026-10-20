"""
DevTwin Backend — Evidence ORM Models
Maps to `evidence`, `evidence_skills`, `evidence_technologies`, and `evidence_concepts`
tables in Migration 001 (001_initial_schema.sql).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.observation import Observation
    from app.models.taxonomy import Concept, Skill, Technology


class Evidence(Base):
    """
    Contextualized, developer-associated interpretation of observations.
    Evidence ≠ Observation. See DOMAIN_MODEL.md.
    """

    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "type IN ('MENTION', 'USAGE', 'APPLIED_ENGINEERING', 'DEMONSTRATED_OUTCOME')",
            name="chk_evidence_type",
        ),
        CheckConstraint(
            "strength BETWEEN 0 AND 1",
            name="chk_evidence_strength",
        ),
        CheckConstraint(
            "directness BETWEEN 0 AND 1",
            name="chk_evidence_directness",
        ),
        CheckConstraint(
            "reliability BETWEEN 0 AND 1",
            name="chk_evidence_reliability",
        ),
        CheckConstraint(
            "polarity BETWEEN -1 AND 1",
            name="chk_evidence_polarity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    observation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("observations.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    strength: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    directness: Mapped[float] = mapped_column(
        Numeric,
        default=1.0,
        nullable=False,
    )
    reliability: Mapped[float] = mapped_column(
        Numeric,
        default=1.0,
        nullable=False,
    )
    polarity: Mapped[float] = mapped_column(
        Numeric,
        nullable=False,
    )
    recency: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    observation: Mapped[Optional["Observation"]] = relationship(
        "Observation",
        back_populates="evidence",
    )

    skills: Mapped[List["Skill"]] = relationship(
        "Skill",
        secondary="evidence_skills",
    )
    technologies: Mapped[List["Technology"]] = relationship(
        "Technology",
        secondary="evidence_technologies",
    )
    concepts: Mapped[List["Concept"]] = relationship(
        "Concept",
        secondary="evidence_concepts",
    )

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} type={self.type} strength={self.strength} polarity={self.polarity}>"


class EvidenceSkill(Base):
    """Junction table: Evidence → Skill it supports."""

    __tablename__ = "evidence_skills"

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )


class EvidenceTechnology(Base):
    """Junction table: Evidence → Technology it supports."""

    __tablename__ = "evidence_technologies"

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
    )
    technology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technologies.id", ondelete="CASCADE"),
        primary_key=True,
    )


class EvidenceConcept(Base):
    """Junction table: Evidence → Concept it supports."""

    __tablename__ = "evidence_concepts"

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )
