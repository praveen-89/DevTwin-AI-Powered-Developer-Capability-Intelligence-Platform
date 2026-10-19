"""
DevTwin Backend — RepositoryDependency ORM Model
Maps to the `repository_dependencies` table in Migration 001 (001_initial_schema.sql).
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import UUID, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class RepositoryDependency(Base):
    """
    Tracked package dependencies per repository.
    """

    __tablename__ = "repository_dependencies"
    __table_args__ = (
        UniqueConstraint("repository_id", "ecosystem", "package_name", name="uq_repo_deps_repo_eco_pkg"),
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
    ecosystem: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    package_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    version_constraint: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    repository: Mapped["Repository"] = relationship(
        "Repository",
        backref="dependencies",
    )

    def __repr__(self) -> str:
        return f"<RepositoryDependency id={self.id} repository_id={self.repository_id} ecosystem={self.ecosystem} package_name={self.package_name}>"
