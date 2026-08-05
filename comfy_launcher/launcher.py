"""
launcher.py — ComfyUI process launcher.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from comfy_launcher.config import Config
from comfy_launcher.gpu import detect_gpu, get_comfyui_launch_args
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver

log = get_logger(__name__)


class Launcher:
    """Manages the ComfyUI server process.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths
        self._process: Optional[subprocess.Popen] = None  # type: ignore[type-arg]

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(
        self,
        port: Optional[int] = None,
        extra_args: Optional[list[str]] = None,
        background: bool = True,
    ) -> Optional[subprocess.Popen]:  # type: ignore[type-arg]
        """Start the ComfyUI server.

        Args:
            port: Port to listen on. Defaults to config value.
            extra_args: Additional CLI arguments for ComfyUI.
            background: If True, runs as a background process.

        Returns:
            The :class:`subprocess.Popen` object, or None on failure.
        """
        if self.is_running:
            log.warning("ComfyUI is already running (PID %d)", self._process.pid)  # type: ignore[union-attr]
            return self._process

        main_py = self._paths.comfyui_main_py
        if not main_py.exists():
            log.error("ComfyUI main.py not found at %s — please install first", main_py)
            return None

        port = port or self._cfg.comfyui_port
        gpu_info = detect_gpu()
        gpu_args = get_comfyui_launch_args(gpu_info)

        cmd = [sys.executable, str(main_py), "--port", str(port)]

        # GPU-based args
        cmd.extend(gpu_args)

        # Config extra args
        if self._cfg.comfyui_extra_args:
            cmd.extend(self._cfg.comfyui_extra_args.split())

        # Caller extra args
        if extra_args:
            cmd.extend(extra_args)

        log.info("Launching ComfyUI: %s", " ".join(cmd))

        env = {**os.environ, "COMFYUI_PORT": str(port)}

        if background:
            self._process = subprocess.Popen(
                cmd,
                cwd=str(self._paths.comfyui_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            log.info("✅ ComfyUI started (PID %d) on port %d", self._process.pid, port)
            self._stream_logs_background()
        else:
            # Blocking — useful for CLI
            subprocess.run(cmd, cwd=str(self._paths.comfyui_dir), env=env, check=False)

        return self._process

    def stop(self) -> None:
        """Stop the ComfyUI server."""
        if self._process and self.is_running:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
            log.info("ComfyUI stopped")
        self._process = None

    def wait(self, url: str = "", timeout: int = 60) -> bool:
        """Wait until ComfyUI is responsive on the given URL.

        Args:
            url: Health-check URL. If empty, builds from config port.
            timeout: Max seconds to wait.

        Returns:
            True if ComfyUI is ready, False on timeout.
        """
        import requests

        if not url:
            url = f"http://localhost:{self._cfg.comfyui_port}"

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = requests.get(url, timeout=3)
                if resp.status_code < 500:
                    log.info("ComfyUI is ready at %s", url)
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)

        log.warning("ComfyUI did not become ready within %d seconds", timeout)
        return False

    def _stream_logs_background(self) -> None:
        """Stream ComfyUI stdout to the logger in a background thread."""
        import threading

        def _reader() -> None:
            if self._process and self._process.stdout:
                for line in self._process.stdout:
                    log.debug("[ComfyUI] %s", line.rstrip())

        t = threading.Thread(target=_reader, daemon=True, name="comfyui-log")
        t.start()
