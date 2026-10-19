"""
DevTwin Backend — SkillGraph Taxonomy ORM Models
Maps to the taxonomy tables in Section 4 of Migration 001 (001_initial_schema.sql):
- skills
- technologies
- concepts
- skill_technologies
- skill_concepts
- technology_concepts
- skill_relationships
"""

import uuid
from typing import Optional

from sqlalchemy import UUID, CheckConstraint, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Skill(Base):
    """
    Broad competency areas (e.g., 'Backend Development'). Global/shared taxonomy.
    """

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )
    domain: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Skill id={self.id} name={self.name}>"


class Technology(Base):
    """
    Concrete implementation technologies (e.g., 'FastAPI'). Global taxonomy.
    """

    __tablename__ = "technologies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )
    type: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,  # e.g. 'language', 'framework', 'tool', 'library'
    )

    def __repr__(self) -> str:
        return f"<Technology id={self.id} name={self.name} type={self.type}>"


class Concept(Base):
    """
    Underlying technical concepts (e.g., 'REST API'). Global taxonomy.
    """

    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Concept id={self.id} name={self.name}>"


class SkillTechnology(Base):
    """
    Junction: Skill ↔ Technology
    """

    __tablename__ = "skill_technologies"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    technology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technologies.id", ondelete="CASCADE"),
        primary_key=True,
    )


class SkillConcept(Base):
    """
    Junction: Skill ↔ Concept
    """

    __tablename__ = "skill_concepts"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )


class TechnologyConcept(Base):
    """
    Junction: Technology ↔ Concept
    """

    __tablename__ = "technology_concepts"

    technology_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("technologies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )


class SkillRelationship(Base):
    """
    Directed edges in the SkillGraph (e.g., React REQUIRES JavaScript).
    """

    __tablename__ = "skill_relationships"
    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('REQUIRES', 'RELATED_TO', 'PART_OF')",
            name="chk_skill_relationships_type",
        ),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relation_type: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
    )
