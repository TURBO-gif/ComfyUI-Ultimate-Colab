"""
examples/download_flux.py — Example: Download a Flux model.

Run with:
    python examples/download_flux.py
"""

from __future__ import annotations

from comfy_launcher.config import get_config
from comfy_launcher.logger import setup_logging
from comfy_launcher.model_manager import ModelManager
from comfy_launcher.paths import get_paths

# Bootstrap
cfg = get_config()
setup_logging(level=cfg.log_level)
paths = get_paths(cfg)

mgr = ModelManager(cfg, paths)

# ── Flux Dev (main model) ─────────────────────────────────────────────────────
# Auto-detected as diffusion_models/ based on URL
flux_dev = mgr.download(
    "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors"
)
print(f"Flux Dev: {flux_dev}")

# ── Flux Text Encoder (T5) ────────────────────────────────────────────────────
t5 = mgr.download(
    "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors"
)
print(f"T5 encoder: {t5}")

# ── CLIP L ────────────────────────────────────────────────────────────────────
clip_l = mgr.download(
    "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors"
)
print(f"CLIP L: {clip_l}")

# ── Flux VAE ──────────────────────────────────────────────────────────────────
vae = mgr.download(
    "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors"
)
print(f"VAE: {vae}")

mgr.print_inventory()
