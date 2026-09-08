"""
DevTwin Backend — Structured Logging

Configures structured logging for the application.
Never logs secrets, connection strings, or credentials.
"""

import logging
import sys


def configure_logging(debug: bool = False) -> None:
    """Configure root logger with a structured format."""
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Prefer module-level usage."""
    return logging.getLogger(name)
