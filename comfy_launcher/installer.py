"""
installer.py — ComfyUI installation and dependency setup.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import git

from comfy_launcher.config import Config
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver
from comfy_launcher.utils import pip_install, pip_install_requirements, run

log = get_logger(__name__)


class Installer:
    """Handles initial ComfyUI installation and dependency setup.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths

    @property
    def is_installed(self) -> bool:
        """Return True if ComfyUI appears to be installed."""
        return self._paths.comfyui_main_py.exists()

    def install(self, force: bool = False) -> None:
        """Clone ComfyUI if not present, otherwise update.

        Args:
            force: If True, re-clone even if already installed.
        """
        if self.is_installed and not force:
            log.info("ComfyUI already installed at %s — updating", self._paths.comfyui_dir)
            self.update()
            return

        log.info("Cloning ComfyUI from %s …", self._cfg.comfyui_repo_url)
        target = self._paths.comfyui_dir

        if target.exists() and force:
            import shutil
            shutil.rmtree(target)

        try:
            git.Repo.clone_from(
                self._cfg.comfyui_repo_url,
                str(target),
                depth=1,
                branch=self._cfg.get("comfyui.branch", "master"),
            )
            log.info("✅ ComfyUI cloned to %s", target)
        except git.GitCommandError as exc:
            log.error("Git clone failed: %s", exc)
            raise RuntimeError(f"ComfyUI clone failed: {exc}") from exc

        self._paths.ensure_comfyui_dirs()
        self.install_requirements()

    def update(self) -> None:
        """Pull the latest ComfyUI changes from the remote."""
        if not self.is_installed:
            log.warning("ComfyUI not installed — installing instead")
            self.install()
            return

        try:
            repo = git.Repo(str(self._paths.comfyui_dir))
            origin = repo.remotes.origin
            origin.pull()
            log.info("✅ ComfyUI updated (HEAD: %s)", repo.head.commit.hexsha[:8])
        except git.GitCommandError as exc:
            log.error("Git pull failed: %s", exc)

    def install_requirements(self) -> None:
        """Install ComfyUI Python requirements."""
        req_file = self._paths.comfyui_dir / "requirements.txt"
        if req_file.exists():
            log.info("Installing ComfyUI requirements …")
            pip_install_requirements(req_file)
        else:
            log.warning("No requirements.txt found in ComfyUI directory")

        # Install any additional missing packages
        self._install_extras()

    def _install_extras(self) -> None:
        """Install extra packages that ComfyUI needs but may be missing."""
        extras = [
            "torch",
            "torchvision",
            "torchaudio",
            "xformers",
            "accelerate",
            "transformers",
            "diffusers",
            "einops",
            "kornia",
            "scipy",
            "scikit-image",
            "Pillow",
            "opencv-python",
        ]
        log.info("Checking/installing extra dependencies …")
        pip_install(extras)

    def get_comfyui_version(self) -> Optional[str]:
        """Return the current ComfyUI git commit hash or None."""
        try:
            repo = git.Repo(str(self._paths.comfyui_dir))
            return repo.head.commit.hexsha[:12]
        except Exception:
            return None

    def status(self) -> dict[str, str | bool]:
        """Return a status dictionary for the dashboard."""
        return {
            "installed": self.is_installed,
            "version": self.get_comfyui_version() or "N/A",
            "dir": str(self._paths.comfyui_dir),
        }
