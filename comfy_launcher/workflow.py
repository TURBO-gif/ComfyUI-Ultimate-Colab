"""
workflow.py — Workflow save/load/export/import/backup manager.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from comfy_launcher.config import Config
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver

log = get_logger(__name__)


@dataclass
class WorkflowRecord:
    """Metadata for a saved workflow."""
    name: str
    path: str
    saved_at: str
    description: str = ""
    tags: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []


class WorkflowManager:
    """Save, load, export and import ComfyUI workflows.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths

    @property
    def workflows_dir(self) -> Path:
        d = self._paths.workflows_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── Save / Load ───────────────────────────────────────────────────────────

    def save(
        self,
        workflow: dict[str, Any],
        name: str,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> Path:
        """Save a workflow dictionary to a JSON file.

        Args:
            workflow: ComfyUI workflow dict.
            name: Workflow name (used as filename).
            description: Optional description.
            tags: Optional list of tag strings.

        Returns:
            Path to the saved file.
        """
        safe_name = name.replace(" ", "_").replace("/", "-")
        if not safe_name.endswith(".json"):
            safe_name += ".json"
        dest = self.workflows_dir / safe_name

        payload: dict[str, Any] = {
            "_meta": {
                "name": name,
                "description": description,
                "tags": tags or [],
                "saved_at": datetime.utcnow().isoformat(),
            },
            "workflow": workflow,
        }
        dest.write_text(json.dumps(payload, indent=2))
        log.info("Saved workflow '%s' to %s", name, dest)
        return dest

    def load(self, name_or_path: str) -> dict[str, Any]:
        """Load a workflow by name or path.

        Args:
            name_or_path: Workflow name (with or without .json) or full path.

        Returns:
            The workflow dict (``"workflow"`` key content).

        Raises:
            FileNotFoundError: If the workflow is not found.
        """
        path = self._resolve_path(name_or_path)
        raw = json.loads(path.read_text())
        return raw.get("workflow", raw)  # Support raw workflow files too

    def delete(self, name_or_path: str) -> None:
        """Delete a workflow file."""
        path = self._resolve_path(name_or_path)
        path.unlink()
        log.info("Deleted workflow: %s", path.name)

    # ── Export / Import ───────────────────────────────────────────────────────

    def export(self, name_or_path: str, dest: Path) -> Path:
        """Export a workflow to an external path.

        Args:
            name_or_path: Workflow name or path.
            dest: Export destination.

        Returns:
            Path to the exported file.
        """
        src = self._resolve_path(name_or_path)
        if dest.is_dir():
            dest = dest / src.name
        shutil.copy2(src, dest)
        log.info("Exported workflow %s → %s", src.name, dest)
        return dest

    def import_workflow(self, src: Path, name: Optional[str] = None) -> Path:
        """Import a workflow JSON from an external path.

        Args:
            src: Source JSON file path.
            name: Optional name override.

        Returns:
            Path to the imported workflow in the workflows directory.
        """
        if not src.exists():
            raise FileNotFoundError(f"Workflow file not found: {src}")

        dest_name = name or src.stem
        raw = json.loads(src.read_text())

        # If it's a raw workflow (no _meta), wrap it
        if "_meta" not in raw:
            return self.save(raw, dest_name)

        dest = self.workflows_dir / src.name
        shutil.copy2(src, dest)
        log.info("Imported workflow: %s", dest.name)
        return dest

    # ── List ──────────────────────────────────────────────────────────────────

    def list_workflows(self) -> list[WorkflowRecord]:
        """List all saved workflows."""
        records = []
        for f in sorted(self.workflows_dir.glob("*.json")):
            try:
                raw = json.loads(f.read_text())
                meta = raw.get("_meta", {})
                records.append(WorkflowRecord(
                    name=meta.get("name", f.stem),
                    path=str(f),
                    saved_at=meta.get("saved_at", ""),
                    description=meta.get("description", ""),
                    tags=meta.get("tags", []),
                ))
            except Exception as exc:
                log.warning("Could not read workflow %s: %s", f.name, exc)
        return records

    def print_list(self) -> None:
        from rich.console import Console
        from rich.table import Table

        workflows = self.list_workflows()
        console = Console()
        table = Table(title=f"Saved Workflows ({len(workflows)})")
        table.add_column("Name", style="bold white", no_wrap=True)
        table.add_column("Saved At", style="cyan")
        table.add_column("Tags", style="dim")
        table.add_column("Description", style="white")

        for wf in workflows:
            table.add_row(
                wf.name,
                wf.saved_at[:19].replace("T", " ") if wf.saved_at else "—",
                ", ".join(wf.tags) if wf.tags else "—",
                wf.description or "—",
            )
        console.print(table)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _resolve_path(self, name_or_path: str) -> Path:
        path = Path(name_or_path)
        if path.is_absolute() and path.exists():
            return path
        # Try workflows dir
        for candidate in [
            self.workflows_dir / name_or_path,
            self.workflows_dir / f"{name_or_path}.json",
        ]:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"Workflow not found: {name_or_path}")
