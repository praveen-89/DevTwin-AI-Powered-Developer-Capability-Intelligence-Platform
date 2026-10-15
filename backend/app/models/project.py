import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.developer import Developer
    from app.models.repository import Repository

class Project(Base):
    """
    Maps to the `projects` table.
    """

    __tablename__ = "projects"

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
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    developer: Mapped["Developer"] = relationship(
        "Developer",
        back_populates="projects"
    )

    repositories: Mapped[list["Repository"]] = relationship(
        "Repository",
        back_populates="project"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name} developer_id={self.developer_id}>"
