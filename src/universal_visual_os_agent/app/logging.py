"""Logging setup for the safe agent skeleton."""

from __future__ import annotations

import logging

from universal_visual_os_agent.config import LoggingConfig


def configure_logging(config: LoggingConfig) -> logging.Logger:
    """Create or reuse the package logger with an idempotent handler."""

    logger = logging.getLogger(config.logger_name)
    logger.setLevel(config.python_level)
    logger.propagate = False

    if not any(getattr(handler, "_uvos_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler._uvos_handler = True  # type: ignore[attr-defined]
        handler.setLevel(config.python_level)
        handler.setFormatter(logging.Formatter(config.format_string))
        logger.addHandler(handler)

    return logger

