"""
DevTwin Backend — GitHubConnectionState ORM Model

Maps to the `github_connection_states` table defined in:
  - database/migrations/004_v02_auth_github.sql
  - database/migrations/005_v02_github_pkce.sql

Security notes:
  - state_hash stores SHA-256(raw_state), never the raw state itself.
  - code_verifier_enc stores Fernet-encrypted PKCE verifier bytes, never plaintext.
  - used_at implements single-use semantics; non-NULL = already claimed.
  - expires_at enforces a short TTL.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UUID, DateTime, LargeBinary, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GitHubConnectionState(Base):
    """
    Maps to the `github_connection_states` table.

    Each row represents a single pending OAuth installation flow initiated by
    a developer. The row is single-use: used_at is set atomically on first claim.
    """

    __tablename__ = "github_connection_states"

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
    # Stores SHA-256(raw_state) — never the raw random state itself.
    state_hash: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Absolute expiry enforced in the claim query (expires_at > NOW()).
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    # NULL = unused/pending. Set atomically on first claim.
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    # Fernet-encrypted PKCE code_verifier bytes.
    # Never plaintext. Added by migration 005.
    code_verifier_enc: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<GitHubConnectionState id={self.id} "
            f"developer_id={self.developer_id} "
            f"used_at={self.used_at}>"
        )
