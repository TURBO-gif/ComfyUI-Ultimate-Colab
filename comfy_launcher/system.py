"""
system.py — System information collection (RAM, disk, CPU, Python, OS).
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from pathlib import Path

import psutil

from comfy_launcher.logger import get_logger
from comfy_launcher.utils import human_size, python_version

log = get_logger(__name__)


@dataclass
class SystemInfo:
    """Snapshot of system resources."""
    os_name: str
    os_version: str
    python_ver: str
    cpu_cores: int
    cpu_threads: int
    ram_total_mb: int
    ram_used_mb: int
    ram_free_mb: int
    disk_total_gb: float
    disk_used_gb: float
    disk_free_gb: float
    disk_path: str

    @property
    def ram_used_pct(self) -> float:
        if self.ram_total_mb == 0:
            return 0.0
        return (self.ram_used_mb / self.ram_total_mb) * 100

    @property
    def disk_used_pct(self) -> float:
        if self.disk_total_gb == 0:
            return 0.0
        return (self.disk_used_gb / self.disk_total_gb) * 100


def get_system_info(disk_path: str = "/") -> SystemInfo:
    """Collect and return current system resource information."""
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(disk_path)

    return SystemInfo(
        os_name=platform.system(),
        os_version=platform.release(),
        python_ver=python_version(),
        cpu_cores=psutil.cpu_count(logical=False) or 1,
        cpu_threads=psutil.cpu_count(logical=True) or 1,
        ram_total_mb=vm.total // (1024 * 1024),
        ram_used_mb=vm.used // (1024 * 1024),
        ram_free_mb=vm.available // (1024 * 1024),
        disk_total_gb=disk.total / (1024**3),
        disk_used_gb=disk.used / (1024**3),
        disk_free_gb=disk.free / (1024**3),
        disk_path=disk_path,
    )


def print_system_summary(info: SystemInfo | None = None) -> None:
    """Pretty-print system information using Rich."""
    from rich.console import Console
    from rich.table import Table

    if info is None:
        info = get_system_info()

    console = Console()
    table = Table(title="System Information", show_header=False, box=None)
    table.add_column("Key", style="cyan bold", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("OS", f"{info.os_name} {info.os_version}")
    table.add_row("Python", info.python_ver)
    table.add_row("CPU Cores", f"{info.cpu_cores} cores / {info.cpu_threads} threads")
    table.add_row(
        "RAM",
        f"{info.ram_used_mb / 1024:.1f} GB / {info.ram_total_mb / 1024:.1f} GB ({info.ram_used_pct:.1f}%)",
    )
    table.add_row(
        "Disk",
        f"{info.disk_used_gb:.1f} GB / {info.disk_total_gb:.1f} GB ({info.disk_used_pct:.1f}%) @ {info.disk_path}",
    )
    console.print(table)
