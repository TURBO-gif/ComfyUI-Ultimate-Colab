"""
tests/test_downloader.py — Unit tests for the Downloader.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses as responses_lib

from comfy_launcher.downloader import Downloader, DownloadResult


@pytest.fixture
def downloader() -> Downloader:
    return Downloader(
        max_retries=1,
        retry_delay=0.0,
        verify_sha256=False,
    )


class TestDownloaderFilename:
    def test_infers_filename_from_url(self, downloader: Downloader, tmp_path: Path) -> None:
        url = "https://example.com/model.safetensors"
        with responses_lib.RequestsMock() as rsps:
            rsps.add(
                responses_lib.GET,
                url,
                body=b"\x00" * 1024,
                status=200,
                headers={"Content-Length": "1024"},
            )
            result = downloader.download(url, tmp_path, progress=False)
        assert result.success
        assert result.dest.name == "model.safetensors"

    def test_override_filename(self, downloader: Downloader, tmp_path: Path) -> None:
        url = "https://example.com/abc123?token=xyz"
        with responses_lib.RequestsMock() as rsps:
            rsps.add(
                responses_lib.GET,
                url,
                body=b"\x00" * 512,
                status=200,
                headers={"Content-Length": "512"},
            )
            result = downloader.download(url, tmp_path, progress=False, filename="my_model.bin")
        assert result.dest.name == "my_model.bin"


class TestDownloaderResume:
    def test_sends_range_header_when_file_exists(
        self, downloader: Downloader, tmp_path: Path
    ) -> None:
        url = "https://example.com/large.bin"
        # Create partial file
        partial = tmp_path / "large.bin"
        partial.write_bytes(b"\x00" * 500)

        with responses_lib.RequestsMock() as rsps:
            rsps.add(
                responses_lib.GET,
                url,
                body=b"\x00" * 500,
                status=206,
                headers={"Content-Length": "500", "Content-Range": "bytes 500-999/1000"},
            )
            result = downloader.download(url, partial, progress=False)
        # Check that Range header was sent
        assert result.success


class TestDownloaderSHA256:
    def test_verification_passes(self, tmp_path: Path) -> None:
        content = b"hello world"
        expected_sha = hashlib.sha256(content).hexdigest()
        url = "https://example.com/verified.bin"

        dl = Downloader(max_retries=1, retry_delay=0.0, verify_sha256=True)
        with responses_lib.RequestsMock() as rsps:
            rsps.add(
                responses_lib.GET,
                url,
                body=content,
                status=200,
                headers={"Content-Length": str(len(content))},
            )
            result = dl.download(url, tmp_path, expected_sha256=expected_sha, progress=False)
        assert result.success
        assert result.sha256 == expected_sha

    def test_verification_fails(self, tmp_path: Path) -> None:
        content = b"hello world"
        url = "https://example.com/bad.bin"

        dl = Downloader(max_retries=1, retry_delay=0.0, verify_sha256=True)
        with responses_lib.RequestsMock() as rsps:
            rsps.add(
                responses_lib.GET,
                url,
                body=content,
                status=200,
                headers={"Content-Length": str(len(content))},
            )
            result = dl.download(url, tmp_path, expected_sha256="wronghash", progress=False)
        assert not result.success
        # File should be removed
        dest = tmp_path / "bad.bin"
        assert not dest.exists()


class TestDownloadResult:
    def test_size_human(self) -> None:
        r = DownloadResult(url="http://x.com/f", dest=Path("/tmp/f"), success=True, size_bytes=1024)
        assert "KB" in r.size_human

    def test_failed_result(self) -> None:
        r = DownloadResult(url="http://x.com/f", dest=Path("/tmp/f"), success=False, error="timeout")
        assert not r.success
        assert r.error == "timeout"
