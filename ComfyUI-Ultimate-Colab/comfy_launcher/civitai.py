"""
civitai.py — CivitAI API client for model discovery and downloading.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

import requests

from comfy_launcher.constants import CIVITAI_URL_PATTERNS, ModelType
from comfy_launcher.logger import get_logger

log = get_logger(__name__)

_CIVITAI_BASE = "https://civitai.com/api/v1"
_CIVITAI_DOWNLOAD_BASE = "https://civitai.com/api/download/models"


def is_civitai_url(url: str) -> bool:
    """Return True if the URL points to CivitAI."""
    return any(pat in url for pat in CIVITAI_URL_PATTERNS)


def _civitai_type_to_model_type(civitai_type: str) -> ModelType:
    """Map a CivitAI model type string to a :class:`ModelType`."""
    mapping = {
        "Checkpoint": ModelType.CHECKPOINTS,
        "LORA": ModelType.LORAS,
        "LoCon": ModelType.LORAS,
        "TextualInversion": ModelType.EMBEDDINGS,
        "VAE": ModelType.VAE,
        "ControlNet": ModelType.CONTROLNET,
        "Upscaler": ModelType.UPSCALE_MODELS,
        "Hypernetwork": ModelType.HYPERNETWORKS,
    }
    return mapping.get(civitai_type, ModelType.CHECKPOINTS)


class CivitAIClient:
    """Client for the CivitAI REST API.

    Args:
        api_key: CivitAI API key (required for adult content and private models).
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "ComfyUI-Ultimate-Colab/1.0"})
        if api_key:
            self._session.headers["Authorization"] = f"Bearer {api_key}"

    def _get(self, endpoint: str, **params: Any) -> dict[str, Any]:
        url = f"{_CIVITAI_BASE}/{endpoint.lstrip('/')}"
        resp = self._session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ── URL parsing ───────────────────────────────────────────────────────────

    def parse_url(self, url: str) -> dict[str, Optional[str]]:
        """Parse a CivitAI URL and extract model_id / version_id.

        Handles:
        - ``https://civitai.com/models/12345``
        - ``https://civitai.com/models/12345?modelVersionId=67890``
        - ``https://civitai.com/api/download/models/67890``
        """
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        result: dict[str, Optional[str]] = {
            "model_id": None,
            "version_id": None,
        }

        # Direct download URL
        m = re.search(r"/api/download/models/(\d+)", parsed.path)
        if m:
            result["version_id"] = m.group(1)
            return result

        # Model page URL
        m = re.search(r"/models/(\d+)", parsed.path)
        if m:
            result["model_id"] = m.group(1)

        if "modelVersionId" in qs:
            result["version_id"] = qs["modelVersionId"][0]

        return result

    # ── API calls ─────────────────────────────────────────────────────────────

    def get_model(self, model_id: str | int) -> dict[str, Any]:
        """Fetch model metadata from the CivitAI API."""
        return self._get(f"models/{model_id}")

    def get_model_version(self, version_id: str | int) -> dict[str, Any]:
        """Fetch model version metadata from the CivitAI API."""
        return self._get(f"model-versions/{version_id}")

    def get_download_url(self, url: str) -> tuple[str, str, ModelType]:
        """Resolve a CivitAI URL to a direct download URL, filename and type.

        Args:
            url: Any CivitAI model or download URL.

        Returns:
            Tuple of (download_url, filename, model_type).
        """
        components = self.parse_url(url)
        version_id = components.get("version_id")
        model_id = components.get("model_id")

        # If we have a direct download URL
        if version_id:
            version = self.get_model_version(version_id)
        elif model_id:
            # Get the latest version
            model = self.get_model(model_id)
            version = model["modelVersions"][0]
        else:
            raise ValueError(f"Cannot parse CivitAI URL: {url}")

        # Extract the primary file
        files = version.get("files", [])
        if not files:
            raise RuntimeError(f"No files found for version {version.get('id')}")

        # Prefer safetensors, then any model file
        primary = next(
            (f for f in files if f.get("primary")),
            files[0],
        )

        download_url = primary["downloadUrl"]
        if self._api_key:
            download_url += f"?token={self._api_key}"

        filename = primary.get("name", "model.safetensors")
        civitai_type = version.get("model", {}).get("type", "Checkpoint")
        model_type = _civitai_type_to_model_type(civitai_type)

        sha256 = primary.get("hashes", {}).get("SHA256")
        log.debug(
            "CivitAI resolved: %s → %s (%s, SHA256: %s)",
            url, filename, model_type.value, sha256 or "N/A"
        )

        return download_url, filename, model_type

    def download(
        self,
        url: str,
        dest_dir: Path,
        show_progress: bool = True,
    ) -> Path:
        """Download a model from CivitAI.

        Args:
            url: CivitAI model page or download URL.
            dest_dir: Destination directory.
            show_progress: Show Rich progress bar.

        Returns:
            Path to the downloaded file.
        """
        try:
            download_url, filename, _ = self.get_download_url(url)
        except Exception as exc:
            # If API lookup fails, try direct download
            log.warning("CivitAI API lookup failed (%s); trying direct URL", exc)
            download_url = url
            filename = None  # type: ignore[assignment]

        dest_dir.mkdir(parents=True, exist_ok=True)

        from comfy_launcher.downloader import Downloader
        dl = Downloader(headers=dict(self._session.headers))
        result = dl.download(
            download_url,
            dest_dir,
            progress=show_progress,
            filename=filename,
        )
        if not result.success:
            raise RuntimeError(f"CivitAI download failed: {result.error}")
        return result.dest
