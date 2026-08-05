"""
updater.py — Auto-updater for ComfyUI and custom nodes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import git

from comfy_launcher.config import Config
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver
from comfy_launcher.utils import pip_install_requirements

log = get_logger(__name__)


class Updater:
    """Handles updating ComfyUI and all custom nodes.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths

    def update_comfyui(self) -> bool:
        """Pull latest ComfyUI from GitHub.

        Returns:
            True if updated, False if already up to date or an error occurred.
        """
        comfy_dir = self._paths.comfyui_dir
        if not comfy_dir.exists():
            log.warning("ComfyUI directory not found — cannot update")
            return False

        try:
            repo = git.Repo(str(comfy_dir))
            before = repo.head.commit.hexsha
            repo.remotes.origin.pull()
            after = repo.head.commit.hexsha
            if before != after:
                log.info("✅ ComfyUI updated: %s → %s", before[:8], after[:8])
                return True
            log.info("ComfyUI already up to date (%s)", before[:8])
            return False
        except git.GitCommandError as exc:
            log.error("ComfyUI update failed: %s", exc)
            return False

    def update_custom_nodes(self) -> dict[str, bool]:
        """Update all custom nodes via git pull.

        Returns:
            Dict mapping node name → True if updated, False otherwise.
        """
        nodes_dir = self._paths.comfyui_custom_nodes_dir
        results: dict[str, bool] = {}

        if not nodes_dir.exists():
            log.warning("Custom nodes directory not found")
            return results

        for node_dir in nodes_dir.iterdir():
            if not node_dir.is_dir():
                continue
            try:
                repo = git.Repo(str(node_dir))
                before = repo.head.commit.hexsha
                repo.remotes.origin.pull()
                after = repo.head.commit.hexsha
                updated = before != after
                results[node_dir.name] = updated
                if updated:
                    log.info("Updated node: %s (%s → %s)", node_dir.name, before[:8], after[:8])
                    # Reinstall requirements after update
                    req_file = node_dir / "requirements.txt"
                    if req_file.exists():
                        pip_install_requirements(req_file)
                else:
                    log.debug("Node already up to date: %s", node_dir.name)
            except git.InvalidGitRepositoryError:
                log.debug("Not a git repo: %s — skipping", node_dir)
                results[node_dir.name] = False
            except git.GitCommandError as exc:
                log.warning("Failed to update node %s: %s", node_dir.name, exc)
                results[node_dir.name] = False

        updated_count = sum(1 for v in results.values() if v)
        log.info("Custom nodes update complete: %d updated, %d total", updated_count, len(results))
        return results

    def update_all(self) -> dict[str, Any]:
        """Update ComfyUI and all custom nodes."""
        comfy_updated = self.update_comfyui()
        node_results = self.update_custom_nodes()
        return {
            "comfyui_updated": comfy_updated,
            "nodes": node_results,
        }
