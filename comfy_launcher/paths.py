"""
paths.py — Centralised path resolution for ComfyUI Ultimate Colab.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from comfy_launcher.config import Config


class PathResolver:
    """Resolves all runtime paths from the active Config."""

    def __init__(self, cfg: "Config") -> None:
        self._cfg = cfg

    @property
    def comfyui_dir(self) -> Path:
        return self._cfg.comfyui_dir

    @property
    def comfyui_models_dir(self) -> Path:
        return self.comfyui_dir / "models"

    @property
    def comfyui_custom_nodes_dir(self) -> Path:
        return self.comfyui_dir / "custom_nodes"

    @property
    def comfyui_input_dir(self) -> Path:
        return self.comfyui_dir / "input"

    @property
    def comfyui_output_dir(self) -> Path:
        return self.comfyui_dir / "output"

    @property
    def comfyui_user_dir(self) -> Path:
        return self.comfyui_dir / "user"

    @property
    def comfyui_main_py(self) -> Path:
        return self.comfyui_dir / "main.py"

    @property
    def drive_root(self) -> Path:
        return self._cfg.drive_root

    def drive_subdir(self, key: str) -> Path:
        rel = self._cfg.get(f"drive.subdirs.{key}", key)
        return self.drive_root.parent.parent / rel

    @property
    def drive_models_dir(self) -> Path:
        return self.drive_subdir("models")

    @property
    def drive_input_dir(self) -> Path:
        return self.drive_subdir("input")

    @property
    def drive_output_dir(self) -> Path:
        return self.drive_subdir("output")

    @property
    def drive_user_dir(self) -> Path:
        return self.drive_subdir("user")

    @property
    def drive_workflows_dir(self) -> Path:
        return self.drive_subdir("workflows")

    @property
    def drive_custom_nodes_dir(self) -> Path:
        return self.drive_subdir("custom_nodes")

    @property
    def drive_downloads_dir(self) -> Path:
        return self.drive_subdir("downloads")

    @property
    def drive_logs_dir(self) -> Path:
        return self.drive_subdir("logs")

    @property
    def drive_backups_dir(self) -> Path:
        return self.drive_subdir("backups")

    @property
    def drive_config_dir(self) -> Path:
        return self.drive_subdir("config")

    def models_dir(self, model_type: str) -> Path:
        rel = self._cfg.model_dirs.get(model_type, f"models/{model_type}")
        return self.comfyui_dir / rel

    @property
    def log_dir(self) -> Path:
        explicit = self._cfg.log_dir
        if explicit:
            return explicit
        drive_logs = self.drive_logs_dir
        if drive_logs.parent.exists():
            return drive_logs
        return self.comfyui_dir / "logs"

    @property
    def backup_dir(self) -> Path:
        explicit = self._cfg.backup_dir
        if explicit:
            return explicit
        drive_backups = self.drive_backups_dir
        if drive_backups.parent.exists():
            return drive_backups
        return self.comfyui_dir / "backups"

    @property
    def workflows_dir(self) -> Path:
        drive_wf = self.drive_workflows_dir
        if drive_wf.parent.exists():
            return drive_wf
        return self.comfyui_user_dir / "default" / "workflows"

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def cloudflared_binary(self) -> Path:
        val = self._cfg.get(
            "tunnel.providers.cloudflare.binary_path", "/content/cloudflared"
        )
        return Path(val)

    def ensure_comfyui_dirs(self) -> None:
        dirs = [
            self.comfyui_input_dir,
            self.comfyui_output_dir,
            self.comfyui_user_dir,
            self.comfyui_custom_nodes_dir,
        ]
        for model_type in self._cfg.model_dirs:
            dirs.append(self.models_dir(model_type))
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def ensure_drive_dirs(self) -> None:
        dirs = [
            self.drive_models_dir,
            self.drive_input_dir,
            self.drive_output_dir,
            self.drive_user_dir,
            self.drive_workflows_dir,
            self.drive_custom_nodes_dir,
            self.drive_downloads_dir,
            self.drive_logs_dir,
            self.drive_backups_dir,
            self.drive_config_dir,
        ]
        for d in dirs:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    def __repr__(self) -> str:
        return f"PathResolver(comfyui_dir={self.comfyui_dir!r})"


_instance: Optional[PathResolver] = None


def get_paths(cfg: Optional["Config"] = None) -> PathResolver:
    global _instance  # noqa: PLW0603
    if _instance is None:
        if cfg is None:
            from comfy_launcher.config import get_config
            cfg = get_config()
        _instance = PathResolver(cfg)
    return _instance


def reset_paths() -> None:
    global _instance  # noqa: PLW0603
    _instance = None
