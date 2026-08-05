"""
huggingface.py — HuggingFace Hub integration.

Supports downloading individual files and resolving model repository
file listings. Uses the official huggingface-hub library when available,
with a fallback to direct HTTPS requests.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote

import requests

from comfy_launcher.constants import HF_URL_PATTERNS
from comfy_launcher.logger import get_logger

log = get_logger(__name__)

_HF_ENDPOINT = "https://huggingface.co"


def _token_header(token: Optional[str]) -> dict[str, str]:
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def is_hf_url(url: str) -> bool:
    """Return True if the URL points to HuggingFace."""
    return any(pat in url for pat in HF_URL_PATTERNS)


def parse_hf_url(url: str) -> dict[str, str]:
    """Parse a HuggingFace URL into components.

    Handles formats:
    - ``https://huggingface.co/{user}/{repo}/resolve/{ref}/{path}``
    - ``https://huggingface.co/{user}/{repo}/blob/{ref}/{path}``

    Returns a dict with keys: user, repo, ref, filepath.
    """
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    result: dict[str, str] = {}

    if len(parts) >= 2:
        result["user"] = parts[0]
        result["repo"] = parts[1]
    if len(parts) >= 4 and parts[2] in ("resolve", "blob"):
        result["ref"] = parts[3]
        result["filepath"] = "/".join(parts[4:])

    return result


def hf_resolve_url(user: str, repo: str, filepath: str, ref: str = "main") -> str:
    """Build a direct download URL for a HuggingFace file."""
    return f"{_HF_ENDPOINT}/{user}/{repo}/resolve/{ref}/{filepath}"


class HuggingFaceClient:
    """Client for downloading files from HuggingFace Hub.

    Args:
        token: Optional HuggingFace API token for gated models.
    """

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token
        self._headers = _token_header(token)

    def resolve_download_url(self, url: str) -> str:
        """Convert any HuggingFace URL to a direct download URL.

        Converts blob/ URLs to resolve/ URLs.

        Args:
            url: Any HuggingFace URL.

        Returns:
            Direct download URL.
        """
        # Convert blob → resolve
        url = url.replace("/blob/", "/resolve/")
        # Ensure we're using the HF endpoint
        return url

    def get_filename(self, url: str) -> str:
        """Extract the filename from a HuggingFace URL."""
        components = parse_hf_url(url)
        filepath = components.get("filepath", "")
        if filepath:
            return filepath.split("/")[-1]
        parsed = urlparse(url)
        return parsed.path.split("/")[-1]

    def download_file(
        self,
        url: str,
        dest_dir: Path,
        filename: Optional[str] = None,
        show_progress: bool = True,
    ) -> Path:
        """Download a file from HuggingFace.

        Tries to use the ``huggingface_hub`` library first, then falls
        back to the :class:`~comfy_launcher.downloader.Downloader`.

        Args:
            url: HuggingFace file URL.
            dest_dir: Directory to save the file in.
            filename: Override filename.
            show_progress: Show download progress.

        Returns:
            Path to the downloaded file.
        """
        direct_url = self.resolve_download_url(url)
        fname = filename or self.get_filename(url)

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / fname

        log.info("Downloading from HuggingFace: %s → %s", fname, dest_dir)

        # Try huggingface_hub first
        try:
            return self._download_via_hub(direct_url, dest_dir, fname)
        except Exception as exc:
            log.debug("huggingface_hub failed (%s), using fallback downloader", exc)

        # Fallback: use our own downloader
        from comfy_launcher.downloader import Downloader
        dl = Downloader(headers=self._headers)
        result = dl.download(direct_url, dest, progress=show_progress)
        if not result.success:
            raise RuntimeError(f"HuggingFace download failed: {result.error}")
        return result.dest

    def _download_via_hub(
        self, url: str, dest_dir: Path, filename: str
    ) -> Path:
        """Use the huggingface_hub library to download."""
        from huggingface_hub import hf_hub_download, snapshot_download  # type: ignore[import]

        components = parse_hf_url(url)
        if not components.get("user") or not components.get("repo"):
            raise ValueError("Cannot parse HuggingFace URL components")

        repo_id = f"{components['user']}/{components['repo']}"
        filepath = components.get("filepath", filename)
        ref = components.get("ref", "main")

        downloaded = hf_hub_download(
            repo_id=repo_id,
            filename=filepath,
            revision=ref,
            token=self._token,
            local_dir=str(dest_dir),
        )
        return Path(downloaded)

    def list_model_files(
        self,
        repo_id: str,
        ref: str = "main",
        extensions: Optional[list[str]] = None,
    ) -> list[str]:
        """List files in a HuggingFace repository.

        Args:
            repo_id: ``user/repo`` identifier.
            ref: Branch or commit hash.
            extensions: Filter to only files with these extensions.

        Returns:
            List of file paths within the repository.
        """
        try:
            from huggingface_hub import list_repo_files  # type: ignore[import]
            files = list(list_repo_files(repo_id, revision=ref, token=self._token))
            if extensions:
                ext_set = {e.lower() for e in extensions}
                files = [f for f in files if any(f.lower().endswith(e) for e in ext_set)]
            return files
        except Exception as exc:
            log.warning("Could not list HF repo files for %s: %s", repo_id, exc)
            return []
