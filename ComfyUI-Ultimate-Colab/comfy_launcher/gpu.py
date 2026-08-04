"""
gpu.py — GPU detection and optimisation helpers.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from comfy_launcher.constants import GPUType
from comfy_launcher.logger import get_logger

log = get_logger(__name__)


@dataclass
class GPUInfo:
    """All relevant GPU information for the current environment."""
    available: bool = False
    gpu_type: GPUType = GPUType.UNKNOWN
    name: str = "N/A"
    vram_total_mb: int = 0
    vram_used_mb: int = 0
    vram_free_mb: int = 0
    cuda_version: str = "N/A"
    driver_version: str = "N/A"
    device_count: int = 0

    @property
    def vram_total_gb(self) -> float:
        return self.vram_total_mb / 1024

    @property
    def vram_used_pct(self) -> float:
        if self.vram_total_mb == 0:
            return 0.0
        return (self.vram_used_mb / self.vram_total_mb) * 100

    @property
    def is_high_end(self) -> bool:
        return self.gpu_type in (GPUType.A100, GPUType.RTX_4090, GPUType.RTX_3090)

    @property
    def supports_fp16(self) -> bool:
        return self.available and self.gpu_type != GPUType.CPU_ONLY


def _classify_gpu(name: str) -> GPUType:
    """Map a GPU name string to a :class:`GPUType` enum value."""
    name_lower = name.lower()
    mapping = {
        "a100": GPUType.A100,
        "l4": GPUType.L4,
        "t4": GPUType.TESLA_T4,
        "v100": GPUType.TESLA_V100,
        "3090": GPUType.RTX_3090,
        "4090": GPUType.RTX_4090,
    }
    for keyword, gpu_type in mapping.items():
        if keyword in name_lower:
            return gpu_type
    return GPUType.UNKNOWN


def _nvidia_smi_query(fields: str) -> Optional[str]:
    """Run nvidia-smi --query-gpu and return stdout, or None on failure."""
    try:
        result = subprocess.run(
            ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def detect_gpu() -> GPUInfo:
    """Detect the current GPU and return a populated :class:`GPUInfo`."""
    info = GPUInfo()

    # ── Try PyTorch first ────────────────────────────────────────────────────
    try:
        import torch
        if torch.cuda.is_available():
            info.available = True
            info.device_count = torch.cuda.device_count()
            info.name = torch.cuda.get_device_name(0)
            info.gpu_type = _classify_gpu(info.name)
            mem = torch.cuda.mem_get_info(0)
            info.vram_free_mb = mem[0] // (1024 * 1024)
            info.vram_total_mb = mem[1] // (1024 * 1024)
            info.vram_used_mb = info.vram_total_mb - info.vram_free_mb
            info.cuda_version = torch.version.cuda or "N/A"
            log.debug("GPU detected via PyTorch: %s", info.name)
            return info
    except ImportError:
        pass

    # ── Fall back to nvidia-smi ──────────────────────────────────────────────
    raw = _nvidia_smi_query(
        "name,memory.total,memory.used,memory.free,driver_version"
    )
    if raw:
        parts = [p.strip() for p in raw.splitlines()[0].split(",")]
        if len(parts) >= 4:
            info.available = True
            info.name = parts[0]
            info.gpu_type = _classify_gpu(info.name)
            try:
                info.vram_total_mb = int(parts[1])
                info.vram_used_mb = int(parts[2])
                info.vram_free_mb = int(parts[3])
            except ValueError:
                pass
            if len(parts) >= 5:
                info.driver_version = parts[4]
            log.debug("GPU detected via nvidia-smi: %s", info.name)
            return info

    # ── CPU only ─────────────────────────────────────────────────────────────
    info.gpu_type = GPUType.CPU_ONLY
    log.info("No CUDA GPU detected — running on CPU")
    return info


def get_comfyui_launch_args(gpu_info: GPUInfo) -> list[str]:
    """Return recommended ComfyUI launch arguments for the detected GPU.

    Args:
        gpu_info: Result of :func:`detect_gpu`.

    Returns:
        List of string arguments to append to the ComfyUI launch command.
    """
    args: list[str] = []

    if not gpu_info.available:
        args.append("--cpu")
        return args

    # FP16 for all CUDA GPUs
    if gpu_info.supports_fp16:
        args.append("--fp16")

    # Low VRAM mode for T4 (16 GB) and smaller
    if gpu_info.vram_total_mb > 0 and gpu_info.vram_total_mb < 20 * 1024:
        args.append("--lowvram")

    # High-end GPUs: use GPU efficient attention
    if gpu_info.is_high_end:
        args.append("--highvram")

    return args


def print_gpu_summary(gpu_info: GPUInfo) -> None:
    """Print a concise GPU summary using Rich."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="GPU Information", show_header=False, box=None)
    table.add_column("Key", style="cyan bold", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("GPU Name", gpu_info.name)
    table.add_row("GPU Type", gpu_info.gpu_type.value)
    table.add_row("CUDA Version", gpu_info.cuda_version)
    table.add_row("Driver", gpu_info.driver_version)
    table.add_row("VRAM Total", f"{gpu_info.vram_total_gb:.1f} GB")
    table.add_row("VRAM Used", f"{gpu_info.vram_used_mb / 1024:.1f} GB ({gpu_info.vram_used_pct:.1f}%)")
    table.add_row("VRAM Free", f"{gpu_info.vram_free_mb / 1024:.1f} GB")
    table.add_row("Device Count", str(gpu_info.device_count))

    console.print(table)
