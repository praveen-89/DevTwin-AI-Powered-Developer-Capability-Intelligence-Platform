"""
DevTwin Backend Tests — Canonical Base Regression

Tests to ensure the single canonical SQLAlchemy DeclarativeBase
is properly used across models, specifically that all models
share the same metadata object.
"""

from app.db.base import Base
from app.models.developer import Developer


def test_canonical_base_metadata():
    """
    Ensure the Developer model uses the exact same metadata object
    as the canonical Base, avoiding duplicate base class definitions.
    """
    assert Developer.metadata is Base.metadata, "Developer model must use canonical Base metadata."


def test_tables_present_in_metadata():
    """
    Ensure the models properly register their tables in the canonical metadata.
    """
    assert "developers" in Base.metadata.tables, "developers table not found in Base.metadata"
