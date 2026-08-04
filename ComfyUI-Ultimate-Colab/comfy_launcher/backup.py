"""
backup.py — Backup and restore functionality for ComfyUI Ultimate Colab.
"""

from __future__ import annotations

import json
import shutil
import tarfile
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from comfy_launcher.config import Config
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver
from comfy_launcher.utils import human_size

log = get_logger(__name__)


@dataclass
class BackupManifest:
    """Metadata stored with each backup archive."""
    id: str
    created_at: str
    includes: list[str]
    size_bytes: int
    comfyui_version: Optional[str] = None
    description: str = ""

    @property
    def size_human(self) -> str:
        return human_size(self.size_bytes)


class BackupManager:
    """Handles backup creation and restoration.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths

    @property
    def backup_dir(self) -> Path:
        d = self._paths.backup_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── List backups ──────────────────────────────────────────────────────────

    def list_backups(self) -> list[BackupManifest]:
        """Return all available backups, sorted newest first."""
        manifests = []
        for mf in sorted(self.backup_dir.glob("*.manifest.json"), reverse=True):
            try:
                data = json.loads(mf.read_text())
                manifests.append(BackupManifest(**data))
            except Exception as exc:
                log.warning("Skipping corrupt manifest %s: %s", mf.name, exc)
        return manifests

    def _get_manifest(self, backup_id: str) -> Optional[BackupManifest]:
        mf_path = self.backup_dir / f"{backup_id}.manifest.json"
        if not mf_path.exists():
            return None
        try:
            return BackupManifest(**json.loads(mf_path.read_text()))
        except Exception:
            return None

    # ── Create backup ─────────────────────────────────────────────────────────

    def create(
        self,
        includes: Optional[list[str]] = None,
        description: str = "",
        compress: Optional[bool] = None,
    ) -> BackupManifest:
        """Create a new backup archive.

        Args:
            includes: List of items to back up. If None, reads from config.
                      Valid values: ``outputs``, ``inputs``, ``workflows``,
                      ``user``, ``models``, ``custom_nodes``.
            description: Human-readable description for this backup.
            compress: Whether to gzip the archive. Defaults to config value.

        Returns:
            The :class:`BackupManifest` for the new backup.
        """
        if includes is None:
            incl_cfg = self._cfg.get("backup.include", {})
            includes = [k for k, v in incl_cfg.items() if v]

        compress = compress if compress is not None else bool(self._cfg.get("backup.compress", True))

        backup_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext = ".tar.gz" if compress else ".tar"
        archive_path = self.backup_dir / f"{backup_id}{ext}"

        log.info("Creating backup %s (includes: %s)", backup_id, includes)

        mode = "w:gz" if compress else "w"
        with tarfile.open(archive_path, mode) as tar:
            for item in includes:
                src = self._item_path(item)
                if src and src.exists():
                    tar.add(str(src), arcname=item)
                    log.debug("Added %s to backup", item)
                else:
                    log.debug("Skipping %s — path not found", item)

        size = archive_path.stat().st_size

        # Prune old backups
        self._prune_backups()

        manifest = BackupManifest(
            id=backup_id,
            created_at=datetime.utcnow().isoformat(),
            includes=includes,
            size_bytes=size,
            description=description,
        )
        mf_path = self.backup_dir / f"{backup_id}.manifest.json"
        mf_path.write_text(json.dumps(asdict(manifest), indent=2))

        log.info("✅ Backup created: %s (%s)", backup_id, human_size(size))
        return manifest

    # ── Restore backup ────────────────────────────────────────────────────────

    def restore(
        self,
        backup_id: str,
        items: Optional[list[str]] = None,
        overwrite: bool = True,
    ) -> None:
        """Restore from a backup.

        Args:
            backup_id: The backup ID (timestamp string).
            items: Specific items to restore. If None, restores all.
            overwrite: Whether to overwrite existing files.
        """
        # Find the archive
        archive = None
        for ext in (".tar.gz", ".tar"):
            candidate = self.backup_dir / f"{backup_id}{ext}"
            if candidate.exists():
                archive = candidate
                break

        if not archive:
            raise FileNotFoundError(f"Backup archive not found for ID: {backup_id}")

        log.info("Restoring backup %s from %s", backup_id, archive)

        with tarfile.open(archive, "r:*") as tar:
            members = tar.getmembers()
            for member in members:
                # Determine which item this belongs to
                top = member.name.split("/")[0]
                if items and top not in items:
                    continue
                dest = self._item_path(top)
                if dest is None:
                    continue
                target = dest.parent / member.name
                if target.exists() and not overwrite:
                    continue
                try:
                    tar.extract(member, path=str(dest.parent))
                except Exception as exc:
                    log.warning("Could not restore %s: %s", member.name, exc)

        log.info("✅ Backup %s restored", backup_id)

    # ── Prune ─────────────────────────────────────────────────────────────────

    def _prune_backups(self) -> None:
        """Remove oldest backups if exceeding max_backups."""
        max_backups = int(self._cfg.get("backup.max_backups", 10))
        manifests = self.list_backups()
        if len(manifests) > max_backups:
            to_delete = manifests[max_backups:]
            for m in to_delete:
                for ext in (".tar.gz", ".tar"):
                    p = self.backup_dir / f"{m.id}{ext}"
                    if p.exists():
                        p.unlink()
                mf = self.backup_dir / f"{m.id}.manifest.json"
                if mf.exists():
                    mf.unlink()
                log.info("Pruned old backup: %s", m.id)

    # ── Path mapping ──────────────────────────────────────────────────────────

    def _item_path(self, item: str) -> Optional[Path]:
        mapping = {
            "outputs": self._paths.comfyui_output_dir,
            "inputs": self._paths.comfyui_input_dir,
            "workflows": self._paths.workflows_dir,
            "user": self._paths.comfyui_user_dir,
            "models": self._paths.comfyui_models_dir,
            "custom_nodes": self._paths.comfyui_custom_nodes_dir,
        }
        return mapping.get(item)

    # ── Rich table ────────────────────────────────────────────────────────────

    def print_list(self) -> None:
        from rich.console import Console
        from rich.table import Table

        backups = self.list_backups()
        console = Console()
        table = Table(title=f"Available Backups ({len(backups)})")
        table.add_column("ID", style="cyan")
        table.add_column("Date", style="white")
        table.add_column("Size", style="green", justify="right")
        table.add_column("Includes", style="dim")
        table.add_column("Description", style="white")

        for b in backups:
            table.add_row(
                b.id,
                b.created_at[:19].replace("T", " "),
                b.size_human,
                ", ".join(b.includes),
                b.description or "—",
            )
        console.print(table)
