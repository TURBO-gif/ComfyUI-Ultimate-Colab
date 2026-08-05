"""
node_manager.py — Custom node installation and management.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import git

from comfy_launcher.config import Config
from comfy_launcher.constants import WELL_KNOWN_NODES
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver
from comfy_launcher.utils import pip_install_requirements

log = get_logger(__name__)


@dataclass
class NodeRecord:
    """Metadata for an installed custom node."""
    name: str
    path: str
    url: Optional[str] = None
    version: Optional[str] = None
    installed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    enabled: bool = True


class NodeManager:
    """Manages ComfyUI custom node installation and updates.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths
        self._registry_path = paths.comfyui_dir / ".node_registry.json"
        self._registry: dict[str, NodeRecord] = {}
        self._load_registry()

    # ── Registry ──────────────────────────────────────────────────────────────

    def _load_registry(self) -> None:
        if self._registry_path.exists():
            try:
                data = json.loads(self._registry_path.read_text())
                self._registry = {k: NodeRecord(**v) for k, v in data.items()}
            except Exception as exc:
                log.warning("Could not load node registry: %s", exc)

    def _save_registry(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self._registry.items()}
        self._registry_path.write_text(json.dumps(data, indent=2))

    # ── Installation ──────────────────────────────────────────────────────────

    def install(self, url: str, name: Optional[str] = None) -> Path:
        """Clone and install a custom node from a git URL.

        Args:
            url: Git repository URL.
            name: Optional directory name override.

        Returns:
            Path to the installed node directory.
        """
        if not name:
            parsed = urlparse(url)
            name = parsed.path.rstrip("/").split("/")[-1]
            name = name.removesuffix(".git")

        node_dir = self._paths.comfyui_custom_nodes_dir / name

        if node_dir.exists():
            log.info("Node '%s' already installed — updating", name)
            return self._update_single(node_dir, url)

        log.info("Installing custom node: %s from %s", name, url)
        self._paths.comfyui_custom_nodes_dir.mkdir(parents=True, exist_ok=True)

        try:
            git.Repo.clone_from(url, str(node_dir), depth=1)
            log.info("✅ Cloned %s", name)
        except git.GitCommandError as exc:
            log.error("Failed to clone %s: %s", url, exc)
            raise RuntimeError(f"Node install failed: {exc}") from exc

        self._install_node_requirements(node_dir)
        self._register_node(name, node_dir, url)
        return node_dir

    def install_defaults(self) -> None:
        """Install all nodes configured in config.json."""
        nodes_config = self._cfg.get("custom_nodes.nodes", [])
        for entry in nodes_config:
            if not entry.get("enabled", True):
                continue
            url = entry.get("url", "")
            name = entry.get("name")
            if url:
                try:
                    self.install(url, name=name)
                except Exception as exc:
                    log.error("Failed to install %s: %s", name or url, exc)

    def install_by_name(self, name: str) -> Optional[Path]:
        """Install a well-known node by its human-readable name.

        Args:
            name: Name from :data:`~comfy_launcher.constants.WELL_KNOWN_NODES`.

        Returns:
            Path to the installed node, or None if not found.
        """
        url = WELL_KNOWN_NODES.get(name)
        if not url:
            log.error("Unknown node name: %s", name)
            return None
        return self.install(url, name=name)

    # ── Update ────────────────────────────────────────────────────────────────

    def _update_single(self, node_dir: Path, url: Optional[str] = None) -> Path:
        try:
            repo = git.Repo(str(node_dir))
            repo.remotes.origin.pull()
            self._install_node_requirements(node_dir)
            log.info("✅ Updated node: %s", node_dir.name)
        except git.GitCommandError as exc:
            log.warning("Could not update %s: %s", node_dir.name, exc)
        return node_dir

    # ── Requirements ──────────────────────────────────────────────────────────

    def _install_node_requirements(self, node_dir: Path) -> None:
        req_file = node_dir / "requirements.txt"
        if req_file.exists() and self._cfg.get("custom_nodes.install_requirements", True):
            pip_install_requirements(req_file)

    # ── Registry ──────────────────────────────────────────────────────────────

    def _register_node(self, name: str, node_dir: Path, url: Optional[str]) -> None:
        try:
            repo = git.Repo(str(node_dir))
            version = repo.head.commit.hexsha[:12]
        except Exception:
            version = None

        self._registry[name] = NodeRecord(
            name=name,
            path=str(node_dir),
            url=url,
            version=version,
        )
        self._save_registry()

    def scan_disk(self) -> list[NodeRecord]:
        """Scan the custom_nodes directory and return found nodes."""
        nodes_dir = self._paths.comfyui_custom_nodes_dir
        found = []
        if not nodes_dir.exists():
            return found
        for d in nodes_dir.iterdir():
            if not d.is_dir():
                continue
            key = d.name
            if key not in self._registry:
                url: Optional[str] = None
                try:
                    repo = git.Repo(str(d))
                    url = repo.remotes.origin.url
                    version = repo.head.commit.hexsha[:12]
                except Exception:
                    version = None
                self._registry[key] = NodeRecord(
                    name=key, path=str(d), url=url, version=version
                )
            found.append(self._registry[key])
        self._save_registry()
        return found

    def list_installed(self) -> list[NodeRecord]:
        return self.scan_disk()

    def print_inventory(self) -> None:
        """Print a Rich table of all installed custom nodes."""
        from rich.console import Console
        from rich.table import Table

        nodes = self.list_installed()
        console = Console()
        table = Table(title=f"Installed Custom Nodes ({len(nodes)} total)", show_lines=False)
        table.add_column("Name", style="bold white", no_wrap=True)
        table.add_column("Version", style="cyan")
        table.add_column("Source URL", style="dim", no_wrap=True)

        for rec in sorted(nodes, key=lambda r: r.name.lower()):
            table.add_row(rec.name, rec.version or "—", (rec.url or "—")[:60])
        console.print(table)
