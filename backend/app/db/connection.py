"""
DevTwin Backend — Async Database Connection

Uses SQLAlchemy with asyncpg for async PostgreSQL access.
Compatible with Supabase's transaction-mode pooler connection strings.

IMPORTANT: DATABASE_URL must use the `postgresql+asyncpg://` scheme.
Never log the DATABASE_URL or any part containing credentials.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Module-level engine and session factory — created once on first import.
_engine = None
_async_session_factory = None


def _get_engine():
    """
    Return the shared async engine, creating it on first call.
    NullPool is used to be compatible with Supabase's transaction-mode pooler.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,  # Never echo SQL in production — it may expose data.
            poolclass=NullPool,
        )
        logger.info("Database engine created (pool class: NullPool)")
    return _engine


def _get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=_get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.
    The session is automatically closed after the request.
    """
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connectivity() -> bool:
    """
    Perform a lightweight connectivity check against the database.
    Returns True on success, False on failure.
    Never raises — callers decide how to handle failures.
    """
    try:
        engine = _get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        # Log the exception type and message but NOT the connection string.
        logger.warning("Database connectivity check failed: %s", type(exc).__name__)
        return False
