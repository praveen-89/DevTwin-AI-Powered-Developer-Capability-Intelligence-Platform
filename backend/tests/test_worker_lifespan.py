"""
DevTwin Backend Tests — In-Process Worker Lifespan

Smoke tests confirming the FastAPI app starts and stops cleanly with
RUN_WORKER_IN_PROCESS both enabled and disabled. Does not re-test worker
job-claiming behavior (already covered by tests/test_worker.py) — only
that the lifespan wiring in app/main.py starts/cancels the background
task without raising.
"""

import asyncio

import pytest


@pytest.fixture
def _clear_settings_cache():
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_app_starts_and_stops_with_worker_disabled(monkeypatch, _clear_settings_cache):
    """Default (RUN_WORKER_IN_PROCESS unset/false): no background task is started."""
    monkeypatch.delenv("RUN_WORKER_IN_PROCESS", raising=False)

    from app.main import create_app

    app = create_app()

    async with app.router.lifespan_context(app):
        pass  # Startup and shutdown must both complete without raising.


@pytest.mark.asyncio
async def test_app_starts_and_stops_with_worker_enabled(monkeypatch, _clear_settings_cache):
    """RUN_WORKER_IN_PROCESS=true: a background worker task is started and cleanly cancelled on shutdown."""
    monkeypatch.setenv("RUN_WORKER_IN_PROCESS", "true")

    # The worker loop would otherwise try to open a real DB connection on its
    # first iteration — patch it to a no-op that just waits to be cancelled,
    # isolating this test to lifespan wiring rather than worker internals
    # (already covered by tests/test_worker.py).
    async def fake_worker_loop(poll_interval: float = 5.0) -> None:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise

    monkeypatch.setattr("app.workers.runner.worker_loop", fake_worker_loop)

    from app.main import create_app

    app = create_app()

    async with app.router.lifespan_context(app):
        await asyncio.sleep(0)  # let the background task actually start
    # Exiting the context cancels the worker task; reaching here without
    # hanging or raising confirms clean shutdown.
