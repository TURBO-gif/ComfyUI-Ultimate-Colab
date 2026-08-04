"""
drive.py — Google Drive integration for ComfyUI Ultimate Colab.

Handles mounting, directory creation, and symlinking of Drive directories
into the ComfyUI installation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from comfy_launcher.config import Config
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver
from comfy_launcher.utils import symlink_or_copy

log = get_logger(__name__)


class DriveManager:
    """Manages Google Drive mounting and directory linking."""

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths

    @property
    def is_mounted(self) -> bool:
        """Return True if Google Drive appears to be mounted."""
        return self._paths.drive_root.parent.exists()

    @property
    def is_enabled(self) -> bool:
        return self._cfg.drive_enabled

    def mount(self, force: bool = False) -> bool:
        """Mount Google Drive.

        This works only inside Google Colab. Outside Colab it's a no-op.

        Args:
            force: If True, remount even if already mounted.

        Returns:
            True if Drive is mounted (or was already mounted), False on error.
        """
        if not self.is_enabled:
            log.info("Drive integration disabled — skipping mount")
            return False

        if self.is_mounted and not force:
            log.info("Google Drive already mounted at %s", self._paths.drive_root.parent)
            return True

        try:
            from google.colab import drive  # type: ignore[import]
            drive.mount(str(self._cfg.drive_mount_point), force_remount=force)
            log.info("Google Drive mounted at %s", self._cfg.drive_mount_point)
            return True
        except ImportError:
            log.warning("google.colab not available — not in Colab environment")
            return False
        except Exception as exc:
            log.error("Failed to mount Google Drive: %s", exc)
            return False

    def ensure_directories(self) -> None:
        """Create all required Google Drive subdirectories."""
        if not self.is_mounted:
            log.warning("Drive not mounted — skipping directory creation")
            return
        self._paths.ensure_drive_dirs()
        log.info("Drive directories verified at %s", self._paths.drive_root)

    def link_models(self) -> None:
        """Symlink Drive model directories into ComfyUI.

        Creates symlinks from ComfyUI model subdirectories to the corresponding
        Google Drive directories so that models persist across sessions.
        """
        if not self.is_mounted:
            log.warning("Drive not mounted — cannot link models")
            return

        comfy_models = self._paths.comfyui_models_dir
        drive_models = self._paths.drive_models_dir

        if not drive_models.exists():
            log.info("Creating Drive models dir: %s", drive_models)
            drive_models.mkdir(parents=True, exist_ok=True)

        # Link each model subfolder
        for model_type, rel_path in self._cfg.model_dirs.items():
            comfy_subdir = self._paths.comfyui_dir / rel_path
            drive_subdir = drive_models / model_type
            drive_subdir.mkdir(parents=True, exist_ok=True)

            # Remove existing dir/link in ComfyUI and replace with symlink
            if comfy_subdir.is_symlink():
                comfy_subdir.unlink()
            elif comfy_subdir.is_dir():
                # Move any existing files to Drive first
                for item in comfy_subdir.iterdir():
                    dest = drive_subdir / item.name
                    if not dest.exists():
                        item.rename(dest)
                comfy_subdir.rmdir()

            comfy_subdir.parent.mkdir(parents=True, exist_ok=True)
            try:
                comfy_subdir.symlink_to(drive_subdir)
                log.debug("Linked %s → %s", comfy_subdir, drive_subdir)
            except OSError as exc:
                log.warning("Could not symlink %s: %s", comfy_subdir, exc)

        log.info("Model directories linked to Google Drive")

    def link_outputs(self) -> None:
        """Symlink ComfyUI output/input/user directories to Drive."""
        if not self.is_mounted:
            return

        link_map = {
            self._paths.comfyui_output_dir: self._paths.drive_output_dir,
            self._paths.comfyui_input_dir: self._paths.drive_input_dir,
            self._paths.comfyui_user_dir: self._paths.drive_user_dir,
        }
        for local, remote in link_map.items():
            remote.mkdir(parents=True, exist_ok=True)
            if local.is_symlink():
                local.unlink()
            elif local.is_dir():
                for item in local.iterdir():
                    dest = remote / item.name
                    if not dest.exists():
                        item.rename(dest)
                local.rmdir()
            try:
                local.symlink_to(remote)
                log.debug("Linked %s → %s", local, remote)
            except OSError as exc:
                log.warning("Could not symlink %s: %s", local, exc)

        log.info("Output directories linked to Google Drive")

    def link_custom_nodes(self) -> None:
        """Symlink the ComfyUI custom_nodes directory to Drive."""
        if not self.is_mounted:
            return

        local = self._paths.comfyui_custom_nodes_dir
        remote = self._paths.drive_custom_nodes_dir
        remote.mkdir(parents=True, exist_ok=True)

        if local.is_symlink():
            local.unlink()
        elif local.is_dir():
            for item in local.iterdir():
                dest = remote / item.name
                if not dest.exists():
                    item.rename(dest)
            local.rmdir()

        try:
            local.symlink_to(remote)
            log.info("Custom nodes linked to Google Drive")
        except OSError as exc:
            log.warning("Could not symlink custom nodes: %s", exc)

    def setup_all(self) -> None:
        """Full Drive setup: mount → create dirs → link all."""
        mounted = self.mount()
        if not mounted:
            return
        self.ensure_directories()
        self.link_models()
        self.link_outputs()
        self.link_custom_nodes()
        log.info("✅ Google Drive setup complete")
