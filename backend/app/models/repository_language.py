"""
DevTwin Backend — RepositoryLanguage ORM Model
Maps to the `repository_languages` table in Migration 001 (001_initial_schema.sql).
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, BigInteger, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class RepositoryLanguage(Base):
    """
    Language breakdown per repository (updated by analysis runs).
    """

    __tablename__ = "repository_languages"
    __table_args__ = (
        UniqueConstraint("repository_id", "language", name="uq_repository_languages_repo_lang"),
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
    language: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    repository: Mapped["Repository"] = relationship(
        "Repository",
        backref="languages",
    )

    def __repr__(self) -> str:
        return f"<RepositoryLanguage id={self.id} repository_id={self.repository_id} language={self.language} bytes={self.bytes}>"
