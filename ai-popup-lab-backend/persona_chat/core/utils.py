# app/core/utils.py
from __future__ import annotations

import logging
from typing import Optional


_LOGGER_NAME = "ask_persona"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a logger configured for console output (PyCharm-friendly).

    Usage:
        from app.core.utils import get_logger
        log = get_logger(__name__)
        log.info("Hello")
    """
    base_name = _LOGGER_NAME
    full_name = base_name if not name else f"{base_name}.{name}"

    logger = logging.getLogger(full_name)
    _configure_root_logger_once()
    return logger


def _configure_root_logger_once() -> None:
    """
    Configure base logger once. Safe to call many times without duplicating handlers.
    """
    root = logging.getLogger(_LOGGER_NAME)

    # Already configured
    if root.handlers:
        return

    root.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Make 3rd-party libs quieter (adjust if needed)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)