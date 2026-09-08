"""
DevTwin — Health Route

Provides two levels of health information:

  GET /health          → Liveness check (API is alive, no DB required)
  GET /health/database → Readiness check (DB reachable)

No sensitive details (credentials, connection strings, stack traces) are
ever exposed through these endpoints.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.connection import check_database_connectivity
from app.core.config import get_settings

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", summary="API liveness check")
async def health_check():
    """
    Returns a 200 OK when the API process is running.
    Does NOT verify database connectivity (use /health/database for that).
    """
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


@router.get("/health/database", summary="Database readiness check")
async def database_health_check():
    """
    Attempts a lightweight SELECT 1 against the configured database.
    Returns 200 when reachable, 503 when unreachable.

    Does NOT expose connection strings, credentials, or stack traces.
    """
    is_connected = await check_database_connectivity()

    if is_connected:
        return {
            "status": "ok",
            "database": "reachable",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    logger.warning("Health check: database is unreachable")
    return JSONResponse(
        status_code=503,
        content={
            "status": "degraded",
            "database": "unreachable",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        },
    )
