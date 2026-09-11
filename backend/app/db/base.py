"""
DevTwin Backend — Canonical ORM Base

This module provides the single canonical SQLAlchemy declarative base
used by all backend models in the application.

Using a single canonical Base ensures that all models share the same
SQLAlchemy MetaData, which is essential for Alembic migrations,
table relationships, and query routing.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Canonical ORM declarative base for all backend models.
    """
    pass
