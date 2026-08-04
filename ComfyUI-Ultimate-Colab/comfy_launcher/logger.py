"""
logger.py — Centralised logging setup for ComfyUI Ultimate Colab.

Provides:
- Rich console handler with coloured output
- Rotating file handler writing to the configured log directory
- A single factory function ``get_logger()`` used throughout the package
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


# ── Module-level Rich console (shared across handlers) ───────────────────────

_console = Console(stderr=True)

# Package-wide root logger name
_ROOT_LOGGER = "comfy_launcher"

# Track whether we've already bootstrapped the root logger
_bootstrapped: bool = False


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    fmt: str = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
) -> logging.Logger:
    """Bootstrap the root ``comfy_launcher`` logger.

    This function is idempotent — calling it more than once only updates
    the log level.  It must be called once during application startup
    (e.g. from the CLI or the notebook) before any module imports.

    Args:
        level: Log level string (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
        log_dir: Directory in which rotating log files are written.
                 If ``None``, file logging is disabled.
        max_bytes: Maximum size of a single log file before rotation.
        backup_count: Number of rotated log files to keep.
        fmt: Log format string used for the file handler.

    Returns:
        The configured root ``comfy_launcher`` logger.
    """
    global _bootstrapped  # noqa: PLW0603

    root = logging.getLogger(_ROOT_LOGGER)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)

    if _bootstrapped:
        # Just update level
        for handler in root.handlers:
            handler.setLevel(numeric_level)
        return root

    # ── Rich console handler ─────────────────────────────────────────────────
    rich_handler = RichHandler(
        console=_console,
        show_time=True,
        show_path=True,
        rich_tracebacks=True,
        markup=True,
        log_time_format="[%H:%M:%S]",
    )
    rich_handler.setLevel(numeric_level)
    root.addHandler(rich_handler)

    # ── Rotating file handler ────────────────────────────────────────────────
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "comfy_launcher.log"

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(file_handler)

    # Prevent propagation to the root Python logger (avoids duplicate output)
    root.propagate = False

    _bootstrapped = True
    return root


def get_logger(name: str = "") -> logging.Logger:
    """Return a child logger under the ``comfy_launcher`` namespace.

    Args:
        name: Dotted sub-name.  If empty, returns the root package logger.

    Returns:
        A :class:`logging.Logger` instance.

    Example::

        log = get_logger(__name__)
        log.info("Hello from %s", __name__)
    """
    if not _bootstrapped:
        # Auto-bootstrap with defaults if not explicitly set up
        setup_logging()

    if name:
        full_name = f"{_ROOT_LOGGER}.{name.removeprefix(_ROOT_LOGGER + '.')}"
    else:
        full_name = _ROOT_LOGGER

    return logging.getLogger(full_name)


def get_console() -> Console:
    """Return the shared Rich :class:`Console` instance."""
    return _console
