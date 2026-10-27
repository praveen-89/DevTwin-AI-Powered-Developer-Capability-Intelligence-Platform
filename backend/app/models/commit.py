"""
DevTwin Backend — Commit ORM Model
Maps to the `commits` table in Migration 001 (001_initial_schema.sql).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import UUID, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class Commit(Base):
    """
    Git commit records. Used for CodeRisk attribution.
    """

    __tablename__ = "commits"
    __table_args__ = (
        UniqueConstraint("repository_id", "sha", name="uq_commits_repo_sha"),
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
    sha: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    author_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    author_email: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    repository: Mapped["Repository"] = relationship("Repository")

    def __repr__(self) -> str:
        return f"<Commit id={self.id} sha={self.sha[:7]}>"
