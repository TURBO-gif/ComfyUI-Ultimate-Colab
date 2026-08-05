"""
github.py — GitHub Releases downloader.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from comfy_launcher.constants import GITHUB_URL_PATTERNS
from comfy_launcher.logger import get_logger

log = get_logger(__name__)

_GH_API = "https://api.github.com"


def is_github_url(url: str) -> bool:
    """Return True if the URL points to GitHub."""
    return any(pat in url for pat in GITHUB_URL_PATTERNS)


class GitHubClient:
    """Client for downloading files from GitHub Releases and raw URLs.

    Args:
        token: Optional GitHub personal access token to avoid rate limits.
    """

    def __init__(self, token: Optional[str] = None) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "ComfyUI-Ultimate-Colab/1.0",
            "Accept": "application/vnd.github+json",
        })
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"

    # ── API helpers ───────────────────────────────────────────────────────────

    def _get(self, url: str, **params: Any) -> Any:
        resp = self._session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_latest_release(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch the latest release metadata."""
        return self._get(f"{_GH_API}/repos/{owner}/{repo}/releases/latest")

    def get_release_assets(
        self,
        owner: str,
        repo: str,
        tag: str = "latest",
    ) -> list[dict[str, Any]]:
        """Return a list of release asset dictionaries."""
        if tag == "latest":
            release = self.get_latest_release(owner, repo)
        else:
            release = self._get(f"{_GH_API}/repos/{owner}/{repo}/releases/tags/{tag}")
        return release.get("assets", [])

    # ── URL parsing ───────────────────────────────────────────────────────────

    def parse_url(self, url: str) -> dict[str, Optional[str]]:
        """Parse a GitHub URL into components.

        Handles:
        - ``https://github.com/{owner}/{repo}/releases/download/{tag}/{asset}``
        - ``https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}``
        - ``https://github.com/{owner}/{repo}/releases/latest``
        """
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        result: dict[str, Optional[str]] = {
            "owner": None,
            "repo": None,
            "tag": None,
            "asset": None,
        }

        if "raw.githubusercontent.com" in url:
            if len(parts) >= 2:
                result["owner"] = parts[0]
                result["repo"] = parts[1]
            return result

        if len(parts) >= 2:
            result["owner"] = parts[0]
            result["repo"] = parts[1]

        # releases/download/{tag}/{asset}
        if len(parts) >= 6 and parts[2] == "releases" and parts[3] == "download":
            result["tag"] = parts[4]
            result["asset"] = parts[5]

        return result

    def resolve_download_url(self, url: str) -> tuple[str, str]:
        """Resolve a GitHub URL to a direct download URL and filename.

        For release pages (not direct asset links), finds the best matching
        asset (prefers binary files over source archives).

        Returns:
            Tuple of (download_url, filename).
        """
        components = self.parse_url(url)

        # Already a direct download URL
        if components.get("asset"):
            return url, components["asset"]

        # Latest release page — find best asset
        owner = components.get("owner") or ""
        repo = components.get("repo") or ""
        tag = components.get("tag") or "latest"

        if not owner or not repo:
            # Treat as direct URL
            filename = url.split("/")[-1]
            return url, filename

        assets = self.get_release_assets(owner, repo, tag)
        if not assets:
            raise RuntimeError(f"No assets in release {owner}/{repo}@{tag}")

        # Prefer Linux AMD64 binaries, then any file
        preferred = next(
            (a for a in assets if "linux" in a["name"].lower() and "amd64" in a["name"].lower()),
            next((a for a in assets if a["name"].endswith(".tar.gz")), assets[0]),
        )
        return preferred["browser_download_url"], preferred["name"]

    def download(
        self,
        url: str,
        dest_dir: Path,
        show_progress: bool = True,
    ) -> Path:
        """Download a file from GitHub.

        Args:
            url: GitHub URL (release page or direct file link).
            dest_dir: Destination directory.
            show_progress: Show Rich progress bar.

        Returns:
            Path to the downloaded file.
        """
        download_url, filename = self.resolve_download_url(url)
        dest_dir.mkdir(parents=True, exist_ok=True)

        from comfy_launcher.downloader import Downloader
        dl = Downloader(headers=dict(self._session.headers))
        result = dl.download(download_url, dest_dir / filename, progress=show_progress)
        if not result.success:
            raise RuntimeError(f"GitHub download failed: {result.error}")
        return result.dest
