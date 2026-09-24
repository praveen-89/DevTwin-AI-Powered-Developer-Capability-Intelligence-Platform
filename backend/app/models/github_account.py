"""
DevTwin Backend — GitHub Account ORM Model

SQLAlchemy model for the `github_accounts` table.
Maps to the schema defined in docs/11_DATABASE_SCHEMA.md,
001_initial_schema.sql, 004_v02_auth_github.sql, and 005_v02_github_pkce.sql.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UUID, BigInteger, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GitHubAccount(Base):
    """
    Maps to the `github_accounts` table.
    Provides a strict 1:1 mapping between a DevTwin Developer and a GitHub Account.
    """

    __tablename__ = "github_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    developer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("developers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    github_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
    )
    username: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    installation_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    disconnected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    developer = relationship("Developer", back_populates="github_account")

    def __repr__(self) -> str:
        return (
            f"<GitHubAccount id={self.id} "
            f"developer_id={self.developer_id} github_id={self.github_id}>"
        )
