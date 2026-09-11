"""
DevTwin Backend — Developer ORM Model

SQLAlchemy model for the `developers` table.
Maps to the schema defined in docs/11_DATABASE_SCHEMA.md and
Migration 001 (001_initial_schema.sql).

This model is read-only from the perspective of the auth dependency.
Developer creation is handled explicitly by POST /developers/me (not yet implemented).
"""

import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base


class Developer(Base):
    """
    Maps to the `developers` table.

    Identity mapping: auth_user_id == Supabase auth.users.id (== JWT sub).
    Internal developer.id is an independent UUIDv4 per ADR-002.
    """

    __tablename__ = "developers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    auth_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Developer id={self.id} auth_user_id={self.auth_user_id}>"
