"""
downloader.py — Core resumable download engine with progress bars.

Supports:
- Resumable downloads (Range header)
- SHA-256 verification
- Rich progress bars
- Retry on failure
- Async parallel downloads
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

import aiohttp
import requests
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from comfy_launcher.logger import get_logger
from comfy_launcher.utils import filename_from_url, human_size, sha256_file

log = get_logger(__name__)

# Chunk size for streaming: 4 MB
_CHUNK_SIZE = 4 * 1024 * 1024


def _make_progress() -> Progress:
    """Create a Rich Progress bar configured for downloads."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=None),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=Console(),
        transient=False,
    )


@dataclass
class DownloadResult:
    """Result of a single download operation."""
    url: str
    dest: Path
    success: bool
    size_bytes: int = 0
    sha256: Optional[str] = None
    elapsed_seconds: float = 0.0
    error: Optional[str] = None

    @property
    def size_human(self) -> str:
        return human_size(self.size_bytes)


class Downloader:
    """Resumable, progress-tracked file downloader.

    Args:
        chunk_size: Download chunk size in bytes.
        max_retries: Number of retry attempts on transient errors.
        retry_delay: Seconds to wait between retries.
        verify_sha256: Whether to verify SHA-256 after download.
        headers: Additional HTTP headers for all requests.
    """

    def __init__(
        self,
        chunk_size: int = _CHUNK_SIZE,
        max_retries: int = 3,
        retry_delay: float = 3.0,
        verify_sha256: bool = True,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.verify_sha256 = verify_sha256
        self._base_headers: dict[str, str] = {
            "User-Agent": "ComfyUI-Ultimate-Colab/1.0",
            **(headers or {}),
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def download(
        self,
        url: str,
        dest: Path,
        expected_sha256: Optional[str] = None,
        progress: bool = True,
        filename: Optional[str] = None,
    ) -> DownloadResult:
        """Download a single file synchronously.

        Args:
            url: Source URL.
            dest: Destination path.  If a directory, the filename is
                  inferred from the URL.
            expected_sha256: If provided, verifies the downloaded file.
            progress: Whether to display a Rich progress bar.
            filename: Override filename (useful when URL has no filename).

        Returns:
            :class:`DownloadResult`
        """
        if dest.is_dir():
            fname = filename or filename_from_url(url)
            dest = dest / fname

        dest.parent.mkdir(parents=True, exist_ok=True)

        for attempt in range(1, self.max_retries + 1):
            try:
                result = self._download_with_resume(url, dest, progress)
                if result.success and expected_sha256 and self.verify_sha256:
                    result = self._verify(result, expected_sha256)
                return result
            except Exception as exc:
                log.warning(
                    "Download attempt %d/%d failed for %s: %s",
                    attempt,
                    self.max_retries,
                    url,
                    exc,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

        return DownloadResult(
            url=url,
            dest=dest,
            success=False,
            error=f"Failed after {self.max_retries} attempts",
        )

    def download_many(
        self,
        tasks: list[tuple[str, Path]],
        progress: bool = True,
    ) -> list[DownloadResult]:
        """Download multiple files, one at a time with a shared progress bar.

        For true parallelism use :meth:`download_many_async`.

        Args:
            tasks: List of ``(url, dest_path)`` tuples.
            progress: Display progress bar.

        Returns:
            List of :class:`DownloadResult`.
        """
        results = []
        for url, dest in tasks:
            results.append(self.download(url, dest, progress=progress))
        return results

    async def download_async(
        self,
        url: str,
        dest: Path,
        session: Optional[aiohttp.ClientSession] = None,
        expected_sha256: Optional[str] = None,
    ) -> DownloadResult:
        """Download a single file asynchronously."""
        if dest.is_dir():
            dest = dest / filename_from_url(url)
        dest.parent.mkdir(parents=True, exist_ok=True)

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession(headers=self._base_headers)

        start = time.monotonic()
        try:
            existing = dest.stat().st_size if dest.exists() else 0
            headers = {**self._base_headers}
            if existing:
                headers["Range"] = f"bytes={existing}-"

            async with session.get(url, headers=headers) as resp:  # type: ignore[union-attr]
                if resp.status == 416:  # Range not satisfiable → file complete
                    size = existing
                else:
                    resp.raise_for_status()
                    mode = "ab" if existing and resp.status == 206 else "wb"
                    size = existing if mode == "ab" else 0
                    async with asyncio.Lock():
                        pass  # placeholder for concurrency control
                    with dest.open(mode) as fh:
                        async for chunk in resp.content.iter_chunked(self.chunk_size):
                            fh.write(chunk)
                            size += len(chunk)

            elapsed = time.monotonic() - start
            result = DownloadResult(
                url=url, dest=dest, success=True,
                size_bytes=size, elapsed_seconds=elapsed,
            )
            if expected_sha256 and self.verify_sha256:
                result = self._verify(result, expected_sha256)
            return result

        except Exception as exc:
            return DownloadResult(url=url, dest=dest, success=False, error=str(exc))
        finally:
            if own_session:
                await session.close()  # type: ignore[union-attr]

    async def download_many_async(
        self,
        tasks: list[tuple[str, Path]],
        concurrency: int = 3,
    ) -> list[DownloadResult]:
        """Download multiple files concurrently."""
        semaphore = asyncio.Semaphore(concurrency)
        connector = aiohttp.TCPConnector(limit=concurrency)
        async with aiohttp.ClientSession(
            headers=self._base_headers, connector=connector
        ) as session:
            async def bounded(url: str, dest: Path) -> DownloadResult:
                async with semaphore:
                    return await self.download_async(url, dest, session=session)

            return list(await asyncio.gather(*[bounded(u, d) for u, d in tasks]))

    # ── Private helpers ───────────────────────────────────────────────────────

    def _download_with_resume(
        self, url: str, dest: Path, show_progress: bool
    ) -> DownloadResult:
        existing_size = dest.stat().st_size if dest.exists() else 0
        headers = {**self._base_headers}
        if existing_size:
            headers["Range"] = f"bytes={existing_size}-"
            log.debug("Resuming download of %s from byte %d", url, existing_size)

        start = time.monotonic()

        with requests.get(url, headers=headers, stream=True, timeout=30) as resp:
            if resp.status_code == 416:
                # File already complete
                size = existing_size
                return DownloadResult(
                    url=url, dest=dest, success=True,
                    size_bytes=size, elapsed_seconds=time.monotonic() - start,
                )
            resp.raise_for_status()

            total = int(resp.headers.get("Content-Length", 0))
            if existing_size and resp.status_code == 206:
                total += existing_size  # Adjust for resume
                mode = "ab"
            else:
                mode = "wb"
                existing_size = 0

            size = existing_size
            fname = dest.name

            if show_progress:
                with _make_progress() as prog:
                    task_id = prog.add_task(
                        description=fname[:40],
                        total=total or None,
                        completed=existing_size,
                    )
                    with dest.open(mode) as fh:
                        for chunk in resp.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                fh.write(chunk)
                                size += len(chunk)
                                prog.update(task_id, advance=len(chunk))
            else:
                with dest.open(mode) as fh:
                    for chunk in resp.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            fh.write(chunk)
                            size += len(chunk)

        elapsed = time.monotonic() - start
        log.info("Downloaded %s → %s (%s in %.1fs)", url, dest, human_size(size), elapsed)
        return DownloadResult(
            url=url, dest=dest, success=True,
            size_bytes=size, elapsed_seconds=elapsed,
        )

    @staticmethod
    def _verify(result: DownloadResult, expected: str) -> DownloadResult:
        """Verify SHA-256 of the downloaded file."""
        if not result.dest.exists():
            result.success = False
            result.error = "File not found after download"
            return result

        log.info("Verifying SHA-256 of %s …", result.dest.name)
        actual = sha256_file(result.dest)
        result.sha256 = actual

        if actual.lower() != expected.lower():
            log.error(
                "SHA-256 mismatch! Expected %s, got %s. Removing file.",
                expected[:16] + "…",
                actual[:16] + "…",
            )
            result.dest.unlink(missing_ok=True)
            result.success = False
            result.error = f"SHA-256 mismatch: expected {expected}, got {actual}"
        else:
            log.info("✅ SHA-256 verified for %s", result.dest.name)

        return result
