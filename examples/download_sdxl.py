"""
examples/download_sdxl.py — Example: Download SDXL + LoRA from CivitAI.

Run with:
    CIVITAI_API_KEY=your_key python examples/download_sdxl.py
"""

from __future__ import annotations

from comfy_launcher.config import get_config
from comfy_launcher.logger import setup_logging
from comfy_launcher.model_manager import ModelManager, ModelType
from comfy_launcher.paths import get_paths

cfg = get_config()
setup_logging()
paths = get_paths(cfg)
mgr = ModelManager(cfg, paths)

# ── SDXL Base from HuggingFace ────────────────────────────────────────────────
sdxl_base = mgr.download(
    "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"
)
print(f"SDXL Base: {sdxl_base}")

# ── SDXL Refiner ─────────────────────────────────────────────────────────────
sdxl_refiner = mgr.download(
    "https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors"
)
print(f"SDXL Refiner: {sdxl_refiner}")

# ── VAE ───────────────────────────────────────────────────────────────────────
vae = mgr.download(
    "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors"
)
print(f"VAE: {vae}")

# ── LoRA from CivitAI (requires API key) ─────────────────────────────────────
# Uncomment and provide a real model ID
# lora = mgr.download("https://civitai.com/models/123456")
# print(f"LoRA: {lora}")

mgr.print_inventory()
