"""
utils.py — Shared utilities for ComfyUI Ultimate Colab.
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar
from urllib.parse import urlparse

from comfy_launcher.logger import get_logger

log = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ── String helpers ────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    return text


def truncate(text: str, max_len: int = 80, suffix: str = "…") -> str:
    """Truncate *text* to *max_len* characters."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def human_size(num_bytes: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0  # type: ignore[assignment]
    return f"{num_bytes:.1f} PB"


def human_duration(seconds: float) -> str:
    """Convert seconds to a human-readable duration string."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m {secs}s"


# ── File / Path helpers ───────────────────────────────────────────────────────

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def safe_remove(path: Path) -> bool:
    """Remove a file or directory tree without raising on error."""
    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        return True
    except OSError as exc:
        log.warning("Could not remove %s: %s", path, exc)
        return False


def symlink_or_copy(src: Path, dst: Path) -> None:
    """Create a symlink from *src* to *dst*; fall back to copy on Windows."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        dst.symlink_to(src)
        log.debug("Symlinked %s → %s", dst, src)
    except (OSError, NotImplementedError):
        shutil.copy2(src, dst)
        log.debug("Copied %s → %s", src, dst)


def is_model_file(path: Path) -> bool:
    """Return True if *path* has a recognised model file extension."""
    from comfy_launcher.constants import MODEL_EXTENSIONS
    return path.suffix.lower() in MODEL_EXTENSIONS


# ── URL helpers ───────────────────────────────────────────────────────────────

def filename_from_url(url: str) -> str:
    """Extract the filename from a URL (last path component)."""
    parsed = urlparse(url)
    name = parsed.path.split("/")[-1]
    # Strip query strings that leaked into the path
    name = name.split("?")[0]
    return name or "download"


def is_url(text: str) -> bool:
    """Return True if *text* looks like an HTTP(S) URL."""
    try:
        result = urlparse(text)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except ValueError:
        return False


# ── Process helpers ───────────────────────────────────────────────────────────

def run(
    cmd: list[str],
    cwd: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
    check: bool = True,
    capture_output: bool = False,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with logging."""
    merged_env = {**os.environ, **(env or {})}
    log.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        text=True,
        capture_output=capture_output,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr or ""
        raise subprocess.CalledProcessError(result.returncode, cmd, stderr=stderr)
    return result


def pip_install(packages: list[str], quiet: bool = True) -> None:
    """Install Python packages via pip."""
    if not packages:
        return
    cmd = [sys.executable, "-m", "pip", "install"] + packages
    if quiet:
        cmd.append("-q")
    log.info("pip install %s", " ".join(packages))
    run(cmd)


def pip_install_requirements(req_file: Path, quiet: bool = True) -> None:
    """Install from a requirements.txt file."""
    if not req_file.exists():
        log.debug("No requirements file at %s", req_file)
        return
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
    if quiet:
        cmd.append("-q")
    log.info("pip install -r %s", req_file)
    run(cmd)


# ── System detection ──────────────────────────────────────────────────────────

def is_colab() -> bool:
    """Return True when running inside Google Colab."""
    try:
        import google.colab  # type: ignore[import]
        return True
    except ImportError:
        return False


def is_linux() -> bool:
    return platform.system() == "Linux"


def is_windows() -> bool:
    return platform.system() == "Windows"


def python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


# ── Retry decorator ───────────────────────────────────────────────────────────

def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry *func* up to *max_attempts* times on *exceptions*."""
    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        log.warning(
                            "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                            attempt,
                            max_attempts,
                            func.__name__,
                            exc,
                            delay,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator


# ── Misc ──────────────────────────────────────────────────────────────────────

def confirm(prompt: str, default: bool = False) -> bool:
    """Ask the user for yes/no confirmation."""
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        answer = input(prompt + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not answer:
        return default
    return answer in ("y", "yes")


def chunk_list(lst: list[Any], size: int) -> list[list[Any]]:
    """Split *lst* into chunks of *size*."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]
