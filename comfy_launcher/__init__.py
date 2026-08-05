"""
ComfyUI Ultimate Colab — comfy_launcher package.

This package provides all backend functionality for the ComfyUI Ultimate Colab
launcher, including installation, model management, tunneling, backup, and more.

Usage::

    from comfy_launcher import Config, Installer, ModelManager

"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "ComfyUI Ultimate Colab Contributors"
__license__ = "MIT"

# Re-export top-level API for convenience
from comfy_launcher.config import Config  # noqa: F401
from comfy_launcher.logger import get_logger  # noqa: F401

__all__ = [
    "__version__",
    "Config",
    "get_logger",
]
