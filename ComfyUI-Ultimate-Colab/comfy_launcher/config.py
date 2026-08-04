"""
config.py — Configuration management for ComfyUI Ultimate Colab.

Loads, validates, and provides typed access to all configuration values.
The configuration hierarchy is (highest priority wins):

1. Environment variables (``COMFY_*``)
2. User-supplied overrides (passed programmatically)
3. ``config.json`` in the project root
4. Built-in defaults

All paths are resolved lazily via :mod:`comfy_launcher.paths`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from comfy_launcher.logger import get_logger

log = get_logger(__name__)

# ── Default config file location ─────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config.json"


class Config:
    """Central configuration object.

    Loads from ``config.json`` and applies environment-variable overrides.
    Access keys using dotted paths::

        cfg = Config()
        port = cfg.get("comfyui.port", default=8188)

    Or use the typed convenience properties below.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        overrides: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialise the configuration.

        Args:
            config_path: Path to a ``config.json`` file.
                         Defaults to the project-root ``config.json``.
            overrides: Dictionary of dotted-path overrides applied after
                       loading the file (useful for tests).
        """
        self._path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}
        self._load()
        self._apply_env_overrides()
        if overrides:
            self._apply_overrides(overrides)

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load configuration from the JSON file."""
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                # Strip private _comment/_version keys
                self._data = {k: v for k, v in raw.items() if not k.startswith("_")}
                log.debug("Loaded config from %s", self._path)
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("Failed to load %s: %s — using defaults", self._path, exc)
                self._data = {}
        else:
            log.debug("No config file at %s — using defaults", self._path)
            self._data = {}

    def _apply_env_overrides(self) -> None:
        """Apply COMFY_* environment variables as dotted-path overrides.

        Variable mapping examples:
        - ``COMFY_COMFYUI__PORT=8080``  →  ``comfyui.port = 8080``
        - ``COMFY_CIVITAI__API_KEY=xyz`` → ``civitai.api_key = xyz``
        (double underscore ``__`` separates sections)
        """
        prefix = "COMFY_"
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            dotted = key[len(prefix):].lower().replace("__", ".")
            self._set_dotted(dotted, self._coerce(value))
            log.debug("Env override: %s = %r", dotted, value)

    def _apply_overrides(self, overrides: dict[str, Any]) -> None:
        for dotted, value in overrides.items():
            self._set_dotted(dotted, value)

    # ── Get / Set helpers ─────────────────────────────────────────────────────

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Retrieve a value by dotted key.

        Args:
            dotted_key: E.g. ``"comfyui.port"`` or ``"tunnel.provider"``.
            default: Returned when the key is not present.

        Returns:
            The config value or *default*.
        """
        parts = dotted_key.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict):
                return default
            node = node.get(part, None)
            if node is None:
                return default
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        """Set a configuration value at runtime (not persisted to disk).

        Args:
            dotted_key: Dotted path.
            value: New value.
        """
        self._set_dotted(dotted_key, value)

    def _set_dotted(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        node: dict[str, Any] = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    @staticmethod
    def _coerce(value: str) -> Any:
        """Attempt to coerce a string env var to a Python type."""
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def save(self, path: Optional[Path] = None) -> None:
        """Persist current configuration to disk.

        Args:
            path: Output path.  Defaults to the loaded config file.
        """
        out = path or self._path
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
        log.info("Configuration saved to %s", out)

    def as_dict(self) -> dict[str, Any]:
        """Return a deep copy of the entire config dictionary."""
        import copy
        return copy.deepcopy(self._data)

    # ── Typed property shortcuts ──────────────────────────────────────────────

    @property
    def comfyui_dir(self) -> Path:
        return Path(self.get("comfyui.dir", "/content/ComfyUI"))

    @property
    def comfyui_port(self) -> int:
        return int(self.get("comfyui.port", 8188))

    @property
    def comfyui_repo_url(self) -> str:
        return str(self.get("comfyui.repo_url", "https://github.com/comfyanonymous/ComfyUI.git"))

    @property
    def comfyui_extra_args(self) -> str:
        return str(self.get("comfyui.extra_args", ""))

    @property
    def drive_enabled(self) -> bool:
        return bool(self.get("drive.enabled", True))

    @property
    def drive_root(self) -> Path:
        return Path(self.get("drive.root", "/content/drive/MyDrive/AI/ComfyUI"))

    @property
    def drive_mount_point(self) -> Path:
        return Path(self.get("drive.mount_point", "/content/drive"))

    @property
    def tunnel_provider(self) -> str:
        return str(self.get("tunnel.provider", "cloudflare"))

    @property
    def tunnel_port(self) -> int:
        return int(self.get("tunnel.port", 8188))

    @property
    def civitai_api_key(self) -> Optional[str]:
        return self.get("civitai.api_key") or os.environ.get("CIVITAI_API_KEY")

    @property
    def hf_token(self) -> Optional[str]:
        return self.get("huggingface.token") or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

    @property
    def log_level(self) -> str:
        return str(self.get("logging.level", "INFO"))

    @property
    def log_dir(self) -> Optional[Path]:
        val = self.get("logging.log_dir")
        return Path(val) if val else None

    @property
    def backup_dir(self) -> Optional[Path]:
        val = self.get("backup.backup_dir")
        return Path(val) if val else None

    @property
    def model_dirs(self) -> dict[str, str]:
        return dict(self.get("models.model_dirs", {}))

    @property
    def verify_sha256(self) -> bool:
        return bool(self.get("models.verify_sha256", True))

    @property
    def resume_downloads(self) -> bool:
        return bool(self.get("models.resume_downloads", True))

    def __repr__(self) -> str:
        return f"Config(path={self._path!r}, keys={list(self._data.keys())})"


# ── Module-level singleton ────────────────────────────────────────────────────

_instance: Optional[Config] = None


def get_config(
    config_path: Optional[Path] = None,
    overrides: Optional[dict[str, Any]] = None,
) -> Config:
    """Return the module-level singleton :class:`Config`.

    On the first call the config is loaded from disk.  Subsequent calls
    return the cached instance (ignoring arguments).  Pass ``overrides``
    on the first call if you need to inject test values.
    """
    global _instance  # noqa: PLW0603
    if _instance is None:
        _instance = Config(config_path=config_path, overrides=overrides)
    return _instance


def reset_config() -> None:
    """Reset the module-level singleton (mainly for testing)."""
    global _instance  # noqa: PLW0603
    _instance = None
