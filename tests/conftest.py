"""
tests/conftest.py — Shared pytest fixtures for ComfyUI Ultimate Colab.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from comfy_launcher.config import Config, reset_config
from comfy_launcher.paths import PathResolver, reset_paths


# ── Temporary directory fixture ───────────────────────────────────────────────

@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Return a clean temporary directory for each test."""
    return tmp_path


# ── Config fixture ─────────────────────────────────────────────────────────────

@pytest.fixture
def config_data(tmp_path: Path) -> dict:
    """Return a minimal config dict for tests."""
    return {
        "comfyui": {
            "repo_url": "https://github.com/comfyanonymous/ComfyUI.git",
            "dir": str(tmp_path / "ComfyUI"),
            "port": 8188,
            "extra_args": "",
            "branch": "master",
        },
        "drive": {
            "enabled": False,
            "mount_point": str(tmp_path / "drive"),
            "root": str(tmp_path / "drive" / "MyDrive" / "AI" / "ComfyUI"),
            "auto_mount": False,
            "subdirs": {
                "comfyui": "ComfyUI",
                "models": "ComfyUI/models",
                "input": "ComfyUI/input",
                "output": "ComfyUI/output",
                "user": "ComfyUI/user",
                "workflows": "ComfyUI/workflows",
                "custom_nodes": "ComfyUI/custom_nodes",
                "downloads": "ComfyUI/downloads",
                "logs": "ComfyUI/logs",
                "backups": "ComfyUI/backups",
                "config": "ComfyUI/config",
            },
        },
        "tunnel": {"provider": "cloudflare", "port": 8188},
        "models": {
            "auto_detect": True,
            "verify_sha256": False,
            "resume_downloads": True,
            "chunk_size_mb": 10,
            "max_retries": 1,
            "retry_delay_seconds": 0,
            "model_dirs": {
                "checkpoints": "models/checkpoints",
                "diffusion_models": "models/diffusion_models",
                "loras": "models/loras",
                "vae": "models/vae",
                "text_encoders": "models/text_encoders",
                "clip": "models/clip",
                "clip_vision": "models/clip_vision",
                "controlnet": "models/controlnet",
                "embeddings": "models/embeddings",
                "upscale_models": "models/upscale_models",
                "unet": "models/unet",
            },
        },
        "civitai": {"api_key": None, "base_url": "https://civitai.com/api/v1"},
        "huggingface": {"token": None, "cache_dir": None},
        "custom_nodes": {
            "auto_update": False,
            "install_requirements": False,
            "nodes": [],
        },
        "backup": {
            "enabled": True,
            "auto_backup": False,
            "max_backups": 5,
            "compress": True,
            "include": {
                "outputs": True,
                "inputs": True,
                "workflows": True,
                "user": True,
                "models": False,
                "custom_nodes": False,
            },
            "backup_dir": str(tmp_path / "backups"),
        },
        "logging": {
            "level": "DEBUG",
            "file_logging": False,
            "log_dir": None,
            "max_bytes": 1048576,
            "backup_count": 1,
            "format": "%(levelname)s %(message)s",
        },
        "dashboard": {"refresh_interval_seconds": 1},
    }


@pytest.fixture
def cfg_file(tmp_path: Path, config_data: dict) -> Path:
    """Write config_data to a temp JSON file and return its path."""
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config_data))
    return path


@pytest.fixture(autouse=True)
def reset_singletons() -> Generator[None, None, None]:
    """Reset module-level singletons between tests."""
    reset_config()
    reset_paths()
    yield
    reset_config()
    reset_paths()


@pytest.fixture
def cfg(cfg_file: Path) -> Config:
    """Return a Config loaded from the temp config file."""
    return Config(config_path=cfg_file)


@pytest.fixture
def paths(cfg: Config) -> PathResolver:
    """Return a PathResolver for the test config."""
    return PathResolver(cfg)
