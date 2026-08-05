"""
dashboard.py — Rich live dashboard for ComfyUI Ultimate Colab.

Displays real-time GPU, RAM, disk, system, ComfyUI version,
model inventory, custom nodes, and tunnel status.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from comfy_launcher.config import Config
from comfy_launcher.gpu import GPUInfo, detect_gpu
from comfy_launcher.logger import get_logger
from comfy_launcher.paths import PathResolver
from comfy_launcher.system import SystemInfo, get_system_info
from comfy_launcher.utils import python_version

log = get_logger(__name__)


# ── Header / Banner ───────────────────────────────────────────────────────────

_BANNER = """
[bold cyan]   ╔═══════════════════════════════════════════════╗[/]
[bold cyan]   ║     [bold white]ComfyUI[/] [bold magenta]Ultimate Colab[/] [bold cyan]v1.0.0          ║[/]
[bold cyan]   ╚═══════════════════════════════════════════════╝[/]
"""


def _make_gpu_panel(gpu: GPUInfo) -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="dim", no_wrap=True)
    table.add_column("Value", style="bold white")

    vram_bar_used = int((gpu.vram_used_mb / max(gpu.vram_total_mb, 1)) * 20)
    vram_bar = "[green]" + "█" * vram_bar_used + "[/][dim]" + "░" * (20 - vram_bar_used) + "[/]"

    table.add_row("GPU", gpu.name or "N/A")
    table.add_row("Type", gpu.gpu_type.value)
    table.add_row("CUDA", gpu.cuda_version)
    table.add_row(
        "VRAM",
        f"{gpu.vram_used_mb/1024:.1f}/{gpu.vram_total_mb/1024:.1f} GB  {vram_bar}  {gpu.vram_used_pct:.1f}%",
    )
    table.add_row("Available", "[green]✓[/]" if gpu.available else "[red]✗[/]")
    return Panel(table, title="[bold cyan]🖥️  GPU[/]", border_style="cyan")


def _make_system_panel(sys_info: SystemInfo) -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="dim", no_wrap=True)
    table.add_column("Value", style="bold white")

    ram_bar_used = int((sys_info.ram_used_mb / max(sys_info.ram_total_mb, 1)) * 20)
    ram_bar = "[blue]" + "█" * ram_bar_used + "[/][dim]" + "░" * (20 - ram_bar_used) + "[/]"

    disk_bar_used = int((sys_info.disk_used_gb / max(sys_info.disk_total_gb, 1)) * 20)
    disk_bar = "[yellow]" + "█" * disk_bar_used + "[/][dim]" + "░" * (20 - disk_bar_used) + "[/]"

    table.add_row("OS", f"{sys_info.os_name} {sys_info.os_version}")
    table.add_row("Python", sys_info.python_ver)
    table.add_row("CPU", f"{sys_info.cpu_cores}c/{sys_info.cpu_threads}t")
    table.add_row(
        "RAM",
        f"{sys_info.ram_used_mb/1024:.1f}/{sys_info.ram_total_mb/1024:.1f} GB  {ram_bar}  {sys_info.ram_used_pct:.1f}%",
    )
    table.add_row(
        "Disk",
        f"{sys_info.disk_used_gb:.1f}/{sys_info.disk_total_gb:.1f} GB  {disk_bar}  {sys_info.disk_used_pct:.1f}%",
    )
    return Panel(table, title="[bold blue]💻  System[/]", border_style="blue")


def _make_status_panel(
    comfyui_version: Optional[str],
    tunnel_url: Optional[str],
    model_count: int,
    node_count: int,
    port: int,
) -> Panel:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="dim", no_wrap=True)
    table.add_column("Value", style="bold white")

    table.add_row("ComfyUI", f"[green]{comfyui_version or 'unknown'}[/]")
    table.add_row("Port", str(port))
    table.add_row(
        "Tunnel",
        f"[green]{tunnel_url}[/]" if tunnel_url else "[dim]not running[/]",
    )
    table.add_row("Models", str(model_count))
    table.add_row("Nodes", str(node_count))
    table.add_row("Time", datetime.now().strftime("%H:%M:%S"))

    return Panel(table, title="[bold magenta]🚀  Status[/]", border_style="magenta")


class Dashboard:
    """Rich live dashboard for ComfyUI Ultimate Colab.

    Args:
        cfg: Active configuration.
        paths: Path resolver.
    """

    def __init__(self, cfg: Config, paths: PathResolver) -> None:
        self._cfg = cfg
        self._paths = paths
        self._console = Console()

    def render_once(
        self,
        tunnel_url: Optional[str] = None,
        comfyui_version: Optional[str] = None,
        model_count: int = 0,
        node_count: int = 0,
    ) -> None:
        """Render the dashboard once (non-live, for notebooks)."""
        gpu = detect_gpu()
        sys_info = get_system_info()

        self._console.print(_BANNER)
        self._console.print(Columns([
            _make_gpu_panel(gpu),
            _make_system_panel(sys_info),
            _make_status_panel(
                comfyui_version,
                tunnel_url,
                model_count,
                node_count,
                self._cfg.comfyui_port,
            ),
        ], equal=True))

    def run_live(
        self,
        tunnel_url: Optional[str] = None,
        comfyui_version: Optional[str] = None,
        refresh_interval: Optional[float] = None,
        stop_after: Optional[int] = None,
    ) -> None:
        """Run the dashboard in live-refresh mode.

        Args:
            tunnel_url: Tunnel URL to display.
            comfyui_version: ComfyUI version string.
            refresh_interval: Seconds between refreshes. Defaults to config value.
            stop_after: Stop after this many seconds (None = run forever).
        """
        interval = refresh_interval or float(
            self._cfg.get("dashboard.refresh_interval_seconds", 5)
        )

        from comfy_launcher.model_manager import ModelManager
        from comfy_launcher.node_manager import NodeManager

        model_mgr = ModelManager(self._cfg, self._paths)
        node_mgr = NodeManager(self._cfg, self._paths)

        start = time.monotonic()

        def _build_layout() -> Layout:
            gpu = detect_gpu()
            sys_info = get_system_info()
            models = model_mgr.scan_disk()
            nodes = node_mgr.scan_disk()

            layout = Layout()
            layout.split_row(
                Layout(_make_gpu_panel(gpu), name="gpu"),
                Layout(_make_system_panel(sys_info), name="system"),
                Layout(
                    _make_status_panel(
                        comfyui_version,
                        tunnel_url,
                        len(models),
                        len(nodes),
                        self._cfg.comfyui_port,
                    ),
                    name="status",
                ),
            )
            return layout

        with Live(
            _build_layout(),
            refresh_per_second=1,
            screen=False,
            console=self._console,
        ) as live:
            while True:
                time.sleep(interval)
                live.update(_build_layout())
                if stop_after and (time.monotonic() - start) >= stop_after:
                    break

    def print_summary(
        self,
        tunnel_url: Optional[str] = None,
        comfyui_version: Optional[str] = None,
    ) -> None:
        """Print a concise one-time summary (suitable for notebook output)."""
        self.render_once(
            tunnel_url=tunnel_url,
            comfyui_version=comfyui_version,
        )
