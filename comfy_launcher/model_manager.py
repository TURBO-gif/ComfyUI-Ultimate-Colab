"""
model_manager.py — Model registry, type detection, and download orchestration.

This is the high-level API for downloading models from any source.
It auto-detects the model type and correct destination folder, then
delegates to the appropriate source client.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from comfy_launcher.civitai import CivitAIClient, is_civitai_url
from comfy_launcher.config import Config
from comfy_launcher.constants import (
    CIVITAI_URL_PATTERNS,
    GITHUB_URL_PATTERNS,
    HF_URL_PATTERNS,
    MODEL_EXTENSIONS,
    MODEL_TYPE_PATTERNS,
    DownloadSource,
    ModelType,
)
from comfy_launcher.github import GitHubClient, is_github_url
from comfy_launcher.huggingface import HuggingFaceClient, is_hf_url
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver
from comfy_launcher.utils import filename_from_url, is_model_file

log = get_logger(__name__)


# ── Model record ──────────────────────────────────────────────────────────────

@dataclass
class ModelRecord:
    """Metadata record for an installed model."""
    name: str
    path: str
    model_type: str
    source_url: Optional[str] = None
    sha256: Optional[str] = None
    size_bytes: int = 0
    installed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def size_human(self) -> str:
        from comfy_launcher.utils import human_size
        return human_size(self.size_bytes)


# ── Model type detection ──────────────────────────────────────────────────────

def detect_model_type(url: str, filename: Optional[str] = None) -> ModelType:
    """Infer the ComfyUI model folder type from a URL and/or filename.

    Uses :data:`~comfy_launcher.constants.MODEL_TYPE_PATTERNS` — first match wins.

    Args:
        url: Download URL.
        filename: Filename hint (optional).

    Returns:
        The inferred :class:`ModelType`.
    """
    combined = f"{url} {filename or ''}".lower()

    for keywords, model_type in MODEL_TYPE_PATTERNS:
        if any(kw in combined for kw in keywords):
            log.debug("Detected model type %s for %s", model_type.value, url[:60])
            return model_type

    return ModelType.CHECKPOINTS  # sensible default


def detect_source(url: str) -> DownloadSource:
    """Determine the download source type from a URL."""
    if is_hf_url(url):
        return DownloadSource.HUGGINGFACE
    if is_civitai_url(url):
        return DownloadSource.CIVITAI
    if is_github_url(url):
        return DownloadSource.GITHUB
    return DownloadSource.DIRECT


# ── Model Manager ─────────────────────────────────────────────────────────────

class ModelManager:
    """High-level model download and registry manager.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths
        self._registry_path = paths.comfyui_dir / ".model_registry.json"
        self._registry: dict[str, ModelRecord] = {}
        self._load_registry()

        # Source clients
        self._hf = HuggingFaceClient(token=cfg.hf_token)
        self._civitai = CivitAIClient(api_key=cfg.civitai_api_key)
        self._github = GitHubClient()

    # ── Registry ──────────────────────────────────────────────────────────────

    def _load_registry(self) -> None:
        if self._registry_path.exists():
            try:
                data = json.loads(self._registry_path.read_text())
                self._registry = {
                    k: ModelRecord(**v) for k, v in data.items()
                }
            except Exception as exc:
                log.warning("Could not load model registry: %s", exc)
                self._registry = {}

    def _save_registry(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self._registry.items()}
        self._registry_path.write_text(json.dumps(data, indent=2))

    def list_installed(self) -> list[ModelRecord]:
        """Return all installed model records from the registry."""
        return list(self._registry.values())

    def scan_disk(self) -> list[ModelRecord]:
        """Scan ComfyUI model directories and return found models.

        Also updates the in-memory registry.
        """
        found = []
        for model_type, rel_path in self._cfg.model_dirs.items():
            dir_path = self._paths.comfyui_dir / rel_path
            if not dir_path.exists():
                continue
            for f in dir_path.iterdir():
                if f.is_file() and is_model_file(f):
                    key = str(f)
                    if key not in self._registry:
                        record = ModelRecord(
                            name=f.name,
                            path=str(f),
                            model_type=model_type,
                            size_bytes=f.stat().st_size,
                        )
                        self._registry[key] = record
                    found.append(self._registry[key])
        self._save_registry()
        log.debug("Disk scan found %d model files", len(found))
        return found

    # ── Download ──────────────────────────────────────────────────────────────

    def download(
        self,
        url: str,
        model_type: Optional[ModelType] = None,
        dest_dir: Optional[Path] = None,
        filename: Optional[str] = None,
        show_progress: bool = True,
    ) -> Path:
        """Download a model from any supported source.

        Auto-detects the source and model type if not specified.

        Args:
            url: Download URL.
            model_type: Override the auto-detected model type.
            dest_dir: Override the destination directory.
            filename: Override the filename.
            show_progress: Display Rich progress bar.

        Returns:
            Path to the downloaded file.
        """
        source = detect_source(url)
        inferred_type = model_type or detect_model_type(url, filename)

        if dest_dir is None:
            dest_dir = self._paths.models_dir(inferred_type.value)
        dest_dir.mkdir(parents=True, exist_ok=True)

        log.info(
            "Downloading model: source=%s type=%s dest=%s",
            source.value, inferred_type.value, dest_dir,
        )

        downloaded_path: Path
        if source == DownloadSource.HUGGINGFACE:
            downloaded_path = self._hf.download_file(
                url, dest_dir, filename=filename, show_progress=show_progress
            )
        elif source == DownloadSource.CIVITAI:
            downloaded_path = self._civitai.download(url, dest_dir, show_progress=show_progress)
        elif source == DownloadSource.GITHUB:
            downloaded_path = self._github.download(url, dest_dir, show_progress=show_progress)
        else:
            # Direct URL
            from comfy_launcher.downloader import Downloader
            dl = Downloader(verify_sha256=self._cfg.verify_sha256)
            result = dl.download(url, dest_dir, progress=show_progress, filename=filename)
            if not result.success:
                raise RuntimeError(f"Download failed: {result.error}")
            downloaded_path = result.dest

        # Update registry
        key = str(downloaded_path)
        record = ModelRecord(
            name=downloaded_path.name,
            path=key,
            model_type=inferred_type.value,
            source_url=url,
            size_bytes=downloaded_path.stat().st_size if downloaded_path.exists() else 0,
        )
        self._registry[key] = record
        self._save_registry()

        log.info("✅ Model downloaded: %s → %s", downloaded_path.name, downloaded_path.parent)
        return downloaded_path

    def download_batch(
        self,
        entries: list[dict[str, Any]],
        show_progress: bool = True,
    ) -> list[Path]:
        """Download a batch of models.

        Args:
            entries: List of dicts with keys ``url`` (required), ``type``
                     (optional), ``filename`` (optional).
            show_progress: Display progress bars.

        Returns:
            List of paths to downloaded files.
        """
        results = []
        for entry in entries:
            url = entry["url"]
            mt_raw = entry.get("type")
            model_type = ModelType(mt_raw) if mt_raw else None
            filename = entry.get("filename")
            try:
                path = self.download(url, model_type=model_type, filename=filename, show_progress=show_progress)
                results.append(path)
            except Exception as exc:
                log.error("Failed to download %s: %s", url, exc)
        return results

    # ── Rich table ────────────────────────────────────────────────────────────

    def print_inventory(self) -> None:
        """Print a Rich table of all installed models."""
        from rich.console import Console
        from rich.table import Table

        models = self.scan_disk()
        console = Console()
        table = Table(title=f"Installed Models ({len(models)} total)", show_lines=False)
        table.add_column("Name", style="bold white", no_wrap=True)
        table.add_column("Type", style="cyan")
        table.add_column("Size", style="green", justify="right")
        table.add_column("Source", style="dim", no_wrap=True)

        for rec in sorted(models, key=lambda r: r.model_type):
            table.add_row(
                rec.name,
                rec.model_type,
                rec.size_human,
                (rec.source_url or "—")[:50],
            )
        console.print(table)
