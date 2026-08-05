"""
tunnel.py — Tunnel management (Cloudflare, Pinggy, LocalTunnel).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from comfy_launcher.config import Config
from comfy_launcher.constants import TunnelProvider
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver

log = get_logger(__name__)

# Regex to extract tunnel URLs from process output
_URL_PATTERNS = [
    re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com"),
    re.compile(r"https://[a-zA-Z0-9\-]+\.a\.pinggy\.io"),
    re.compile(r"https://[a-zA-Z0-9\-]+\.loca\.lt"),
]


class TunnelProcess:
    """Represents a running tunnel process."""

    def __init__(
        self,
        provider: TunnelProvider,
        url: str,
        process: subprocess.Popen,  # type: ignore[type-arg]
    ) -> None:
        self.provider = provider
        self.url = url
        self.process = process
        self.started_at = time.time()

    @property
    def is_alive(self) -> bool:
        return self.process.poll() is None

    def stop(self) -> None:
        if self.is_alive:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        log.info("Tunnel process stopped")

    def __repr__(self) -> str:
        return f"TunnelProcess(provider={self.provider.value!r}, url={self.url!r})"


class TunnelManager:
    """Manages tunnel processes for ComfyUI access.

    Supports Cloudflare Tunnel (default), Pinggy, and LocalTunnel.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths
        self._current: Optional[TunnelProcess] = None

    @property
    def current(self) -> Optional[TunnelProcess]:
        return self._current

    @property
    def is_running(self) -> bool:
        return self._current is not None and self._current.is_alive

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, provider: Optional[str] = None, port: Optional[int] = None) -> Optional[str]:
        """Start a tunnel.

        Args:
            provider: Override the configured tunnel provider.
            port: Override the configured port.

        Returns:
            The public tunnel URL, or None on failure.
        """
        provider_name = provider or self._cfg.tunnel_provider
        port = port or self._cfg.tunnel_port

        try:
            tp = TunnelProvider(provider_name)
        except ValueError:
            log.error("Unknown tunnel provider: %s", provider_name)
            return None

        log.info("Starting %s tunnel on port %d …", tp.value, port)

        if tp == TunnelProvider.CLOUDFLARE:
            return self._start_cloudflare(port)
        elif tp == TunnelProvider.PINGGY:
            return self._start_pinggy(port)
        elif tp == TunnelProvider.LOCALTUNNEL:
            return self._start_localtunnel(port)
        return None

    def stop(self) -> None:
        """Stop the current tunnel."""
        if self._current:
            self._current.stop()
            self._current = None

    def restart(self) -> Optional[str]:
        """Stop and restart the current tunnel."""
        provider = self._current.provider.value if self._current else None
        self.stop()
        time.sleep(2)
        return self.start(provider=provider)

    # ── Cloudflare ────────────────────────────────────────────────────────────

    def _ensure_cloudflared(self) -> Path:
        """Download cloudflared binary if not present."""
        binary = self._paths.cloudflared_binary
        if binary.exists():
            return binary

        url = self._cfg.get(
            "tunnel.providers.cloudflare.binary_url",
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        )
        log.info("Downloading cloudflared …")
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        binary.parent.mkdir(parents=True, exist_ok=True)
        with binary.open("wb") as fh:
            for chunk in resp.iter_content(8192):
                fh.write(chunk)
        binary.chmod(0o755)
        log.info("cloudflared downloaded to %s", binary)
        return binary

    def _start_cloudflare(self, port: int) -> Optional[str]:
        binary = self._ensure_cloudflared()
        cmd = [str(binary), "tunnel", "--url", f"http://localhost:{port}"]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        url = self._read_url_from_output(proc, timeout=30)
        if url:
            self._current = TunnelProcess(TunnelProvider.CLOUDFLARE, url, proc)
            log.info("✅ Cloudflare tunnel active: %s", url)
        else:
            proc.terminate()
            log.error("Failed to get Cloudflare tunnel URL")
        return url

    # ── Pinggy ────────────────────────────────────────────────────────────────

    def _start_pinggy(self, port: int) -> Optional[str]:
        token = self._cfg.get("tunnel.providers.pinggy.token", "")
        if token:
            host = f"{token}@a.pinggy.io"
        else:
            host = "a.pinggy.io"

        cmd = ["ssh", "-p", "443", "-R", f"0:localhost:{port}", "-o", "StrictHostKeyChecking=no", host]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        url = self._read_url_from_output(proc, timeout=20)
        if url:
            self._current = TunnelProcess(TunnelProvider.PINGGY, url, proc)
            log.info("✅ Pinggy tunnel active: %s", url)
        return url

    # ── LocalTunnel ───────────────────────────────────────────────────────────

    def _start_localtunnel(self, port: int) -> Optional[str]:
        subdomain = self._cfg.get("tunnel.providers.localtunnel.subdomain", "")
        cmd = ["npx", "localtunnel", "--port", str(port)]
        if subdomain:
            cmd += ["--subdomain", subdomain]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        url = self._read_url_from_output(proc, timeout=20)
        if url:
            self._current = TunnelProcess(TunnelProvider.LOCALTUNNEL, url, proc)
            log.info("✅ LocalTunnel active: %s", url)
        return url

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _read_url_from_output(
        proc: subprocess.Popen,  # type: ignore[type-arg]
        timeout: int = 30,
    ) -> Optional[str]:
        """Read tunnel process output and extract the public URL."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if proc.stdout is None:
                break
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
                continue
            log.debug("Tunnel output: %s", line.rstrip())
            for pattern in _URL_PATTERNS:
                m = pattern.search(line)
                if m:
                    return m.group(0)
        return None
