"""
cli.py — Full CLI for ComfyUI Ultimate Colab using Click.

Commands:
    install     Clone/update ComfyUI
    update      Update ComfyUI and nodes
    launch      Start ComfyUI + tunnel
    download    Download a model
    nodes       Custom node subcommands
    backup      Create a backup
    restore     Restore from backup
    status      Show system/ComfyUI status
    dashboard   Run the live dashboard
    clean       Remove ComfyUI installation
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from comfy_launcher.config import get_config
from comfy_launcher.logger import get_logger, setup_logging
from comfy_launcher.paths import get_paths

console = Console()
log = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_cfg_and_paths(config_file: Optional[str] = None):  # type: ignore[return]
    cfg = get_config(config_path=Path(config_file) if config_file else None)
    setup_logging(level=cfg.log_level, log_dir=cfg.log_dir)
    paths = get_paths(cfg)
    return cfg, paths


# ── Root group ────────────────────────────────────────────────────────────────

@click.group()
@click.version_option("1.0.0", prog_name="comfy-launcher")
@click.option("--config", "-c", default=None, help="Path to config.json")
@click.pass_context
def main(ctx: click.Context, config: Optional[str]) -> None:
    """ComfyUI Ultimate Colab — Production launcher for ComfyUI."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


# ── install ───────────────────────────────────────────────────────────────────

@main.command("install")
@click.option("--force", is_flag=True, help="Force re-clone even if installed")
@click.pass_context
def cmd_install(ctx: click.Context, force: bool) -> None:
    """Clone ComfyUI (or update if already installed)."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.installer import Installer
    installer = Installer(cfg, paths)
    installer.install(force=force)
    console.print("[green]✅ Install complete[/]")


# ── update ────────────────────────────────────────────────────────────────────

@main.command("update")
@click.option("--nodes/--no-nodes", default=True, help="Also update custom nodes")
@click.pass_context
def cmd_update(ctx: click.Context, nodes: bool) -> None:
    """Update ComfyUI and optionally all custom nodes."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.updater import Updater
    updater = Updater(cfg, paths)
    updater.update_comfyui()
    if nodes:
        updater.update_custom_nodes()
    console.print("[green]✅ Update complete[/]")


# ── launch ────────────────────────────────────────────────────────────────────

@main.command("launch")
@click.option("--port", "-p", default=None, type=int, help="Port to run ComfyUI on")
@click.option("--no-tunnel", is_flag=True, help="Skip starting a tunnel")
@click.option("--tunnel-provider", default=None, help="Tunnel provider override")
@click.pass_context
def cmd_launch(
    ctx: click.Context,
    port: Optional[int],
    no_tunnel: bool,
    tunnel_provider: Optional[str],
) -> None:
    """Start ComfyUI and optionally a tunnel."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.launcher import Launcher
    from comfy_launcher.tunnel import TunnelManager

    launcher = Launcher(cfg, paths)
    launcher.start(port=port, background=not no_tunnel)

    if not no_tunnel:
        tm = TunnelManager(cfg, paths)
        url = tm.start(provider=tunnel_provider)
        if url:
            console.print(f"\n[bold green]🌐 ComfyUI is accessible at: {url}[/]\n")
        # Keep process alive
        try:
            launcher._process.wait()  # type: ignore[union-attr]
        except KeyboardInterrupt:
            launcher.stop()
            tm.stop()


# ── download ──────────────────────────────────────────────────────────────────

@main.command("download")
@click.argument("url")
@click.option("--type", "-t", "model_type", default=None, help="Model type override (e.g. loras)")
@click.option("--filename", "-f", default=None, help="Override filename")
@click.option("--no-verify", is_flag=True, help="Skip SHA-256 verification")
@click.pass_context
def cmd_download(
    ctx: click.Context,
    url: str,
    model_type: Optional[str],
    filename: Optional[str],
    no_verify: bool,
) -> None:
    """Download a model from any supported source."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.model_manager import ModelManager, ModelType

    if no_verify:
        cfg.set("models.verify_sha256", False)

    mgr = ModelManager(cfg, paths)
    mt = ModelType(model_type) if model_type else None

    path = mgr.download(url, model_type=mt, filename=filename)
    console.print(f"[green]✅ Downloaded: {path}[/]")


# ── nodes subgroup ────────────────────────────────────────────────────────────

@main.group("nodes")
def cmd_nodes() -> None:
    """Manage custom nodes."""


@cmd_nodes.command("install")
@click.argument("url_or_name")
@click.pass_context
def cmd_nodes_install(ctx: click.Context, url_or_name: str) -> None:
    """Install a custom node by URL or well-known name."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.node_manager import NodeManager
    from comfy_launcher.constants import WELL_KNOWN_NODES

    mgr = NodeManager(cfg, paths)
    if url_or_name in WELL_KNOWN_NODES:
        mgr.install_by_name(url_or_name)
    else:
        mgr.install(url_or_name)
    console.print("[green]✅ Node installed[/]")


@cmd_nodes.command("list")
@click.pass_context
def cmd_nodes_list(ctx: click.Context) -> None:
    """List installed custom nodes."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.node_manager import NodeManager
    NodeManager(cfg, paths).print_inventory()


@cmd_nodes.command("update")
@click.pass_context
def cmd_nodes_update(ctx: click.Context) -> None:
    """Update all installed custom nodes."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.updater import Updater
    Updater(cfg, paths).update_custom_nodes()
    console.print("[green]✅ Nodes updated[/]")


# ── backup ────────────────────────────────────────────────────────────────────

@main.command("backup")
@click.option("--include", "-i", multiple=True, help="Items to include (outputs, models, …)")
@click.option("--description", "-d", default="", help="Backup description")
@click.pass_context
def cmd_backup(ctx: click.Context, include: tuple[str, ...], description: str) -> None:
    """Create a backup archive."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.backup import BackupManager
    mgr = BackupManager(cfg, paths)
    items = list(include) or None
    manifest = mgr.create(includes=items, description=description)
    console.print(f"[green]✅ Backup created: {manifest.id} ({manifest.size_human})[/]")


# ── restore ───────────────────────────────────────────────────────────────────

@main.command("restore")
@click.argument("backup_id")
@click.option("--items", "-i", multiple=True, help="Specific items to restore")
@click.pass_context
def cmd_restore(ctx: click.Context, backup_id: str, items: tuple[str, ...]) -> None:
    """Restore from a backup."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.backup import BackupManager
    mgr = BackupManager(cfg, paths)
    mgr.restore(backup_id, items=list(items) or None)
    console.print(f"[green]✅ Restored backup: {backup_id}[/]")


# ── status ────────────────────────────────────────────────────────────────────

@main.command("status")
@click.pass_context
def cmd_status(ctx: click.Context) -> None:
    """Show system and ComfyUI status."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.gpu import detect_gpu, print_gpu_summary
    from comfy_launcher.system import get_system_info, print_system_summary
    from comfy_launcher.installer import Installer

    print_gpu_summary(detect_gpu())
    print_system_summary(get_system_info())
    installer = Installer(cfg, paths)
    status = installer.status()
    console.print(f"\n[cyan]ComfyUI Status[/]")
    console.print(f"  Installed : {status['installed']}")
    console.print(f"  Version   : {status['version']}")
    console.print(f"  Directory : {status['dir']}")


# ── dashboard ─────────────────────────────────────────────────────────────────

@main.command("dashboard")
@click.option("--live", is_flag=True, help="Run in live-refresh mode")
@click.option("--refresh", default=5.0, help="Refresh interval in seconds")
@click.pass_context
def cmd_dashboard(ctx: click.Context, live: bool, refresh: float) -> None:
    """Show the live dashboard."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    from comfy_launcher.dashboard import Dashboard
    dash = Dashboard(cfg, paths)
    if live:
        dash.run_live(refresh_interval=refresh)
    else:
        dash.render_once()


# ── clean ─────────────────────────────────────────────────────────────────────

@main.command("clean")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def cmd_clean(ctx: click.Context, yes: bool) -> None:
    """Remove the ComfyUI installation directory."""
    cfg, paths = _get_cfg_and_paths(ctx.obj.get("config"))
    comfy_dir = paths.comfyui_dir
    if not comfy_dir.exists():
        console.print("[yellow]ComfyUI directory not found — nothing to clean[/]")
        return
    if not yes:
        confirm = click.confirm(f"Delete {comfy_dir}?", default=False)
        if not confirm:
            console.print("Aborted.")
            return
    import shutil
    shutil.rmtree(comfy_dir)
    console.print(f"[green]✅ Removed {comfy_dir}[/]")


if __name__ == "__main__":
    main()
