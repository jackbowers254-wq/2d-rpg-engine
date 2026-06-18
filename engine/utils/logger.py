"""
engine.utils.logger
====================
Thin wrapper over the stdlib ``logging`` module so every engine subsystem logs
in a consistent format and respects the ``debug.log_level`` config option.
"""

from __future__ import annotations

import logging

_CONFIGURED = False

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def configure_logging(level: str = "info") -> None:
    """Set up root logging once, using a level name from config."""
    global _CONFIGURED
    logging.basicConfig(
        level=_LEVELS.get(str(level).lower(), logging.INFO),
        format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger, configuring logging on first use."""
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
