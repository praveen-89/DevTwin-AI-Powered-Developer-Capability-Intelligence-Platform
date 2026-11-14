"""
DevTwin Backend — Application Entry Point

Creates and configures the FastAPI application.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.routes import health as health_router
from app.api.routes import developers as developers_router
from app.api.routes import github as github_router
from app.api.routes import projects as projects_router
from app.api.routes import repositories as repositories_router
from app.api.routes import analysis as analysis_router

def create_app() -> FastAPI:
    """
    Application factory. Creates and returns the configured FastAPI instance.
    Called once at import time by the ASGI server.
    """
    # ── Configuration ──────────────────────────────────────────────
    # Fail fast: raises ValidationError if required env vars are absent.
    try:
        settings = get_settings()
    except ValidationError as exc:
        # Cannot start without valid configuration. Print clearly and exit.
        import sys
        print("FATAL: Missing required environment variables:\n", exc)
        sys.exit(1)

    # ── Logging ────────────────────────────────────────────────────
    configure_logging(debug=settings.DEBUG)
    logger = logging.getLogger(__name__)
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # ── In-process worker lifespan (optional) ───────────────────────
    # Runs the existing analysis worker loop as a background asyncio task
    # inside this same process when no separate worker process/service is
    # available (see RUN_WORKER_IN_PROCESS in app/core/config.py). The
    # worker's own entrypoint is reused as-is — its job-claiming logic is
    # never duplicated here. When the flag is false (default), this is a
    # no-op and behavior is unchanged from the original two-process setup.
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        worker_task: asyncio.Task | None = None
        if settings.RUN_WORKER_IN_PROCESS:
            from app.workers.runner import worker_loop

            logger.info("RUN_WORKER_IN_PROCESS enabled — starting analysis worker loop in-process.")
            worker_task = asyncio.create_task(worker_loop())

        try:
            yield
        finally:
            if worker_task is not None:
                logger.info("Stopping in-process analysis worker loop.")
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

    # ── FastAPI Application ─────────────────────────────────────────
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-Powered Developer Capability Intelligence Platform",
        # Disable docs in production by checking DEBUG flag.
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────
    # Only allow explicitly configured origins. Never use wildcard "*" in prod.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Global Exception Handler ───────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Catch-all exception handler. Returns a generic 500 response.
        Never leaks stack traces or internal error details to the client.
        """
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred."},
        )

    # ── Routes ─────────────────────────────────────────────────────
    app.include_router(health_router.router)
    app.include_router(developers_router.router)
    app.include_router(github_router.router)
    app.include_router(projects_router.router)
    app.include_router(repositories_router.router)
    app.include_router(analysis_router.router)

    logger.info("Application startup complete.")
    return app


# The ASGI app object used by uvicorn / gunicorn.
app = create_app()
