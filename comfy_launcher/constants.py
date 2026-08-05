"""
constants.py — All enumerations, string constants, and immutable lookup tables.

No hardcoded values should exist elsewhere in the package; import from here.
"""

from __future__ import annotations

from enum import Enum, auto


# ── GPU / Accelerator types ──────────────────────────────────────────────────

class GPUType(str, Enum):
    """Known GPU categories in Google Colab and local environments."""
    UNKNOWN = "unknown"
    TESLA_T4 = "tesla_t4"
    TESLA_V100 = "tesla_v100"
    A100 = "a100"
    L4 = "l4"
    RTX_3090 = "rtx_3090"
    RTX_4090 = "rtx_4090"
    CPU_ONLY = "cpu_only"


# ── Tunnel providers ─────────────────────────────────────────────────────────

class TunnelProvider(str, Enum):
    """Supported tunnel providers."""
    CLOUDFLARE = "cloudflare"
    PINGGY = "pinggy"
    LOCALTUNNEL = "localtunnel"


# ── Download sources ─────────────────────────────────────────────────────────

class DownloadSource(str, Enum):
    """Supported download source types."""
    HUGGINGFACE = "huggingface"
    CIVITAI = "civitai"
    GITHUB = "github"
    DIRECT = "direct"
    UNKNOWN = "unknown"


# ── Model types / folders ────────────────────────────────────────────────────

class ModelType(str, Enum):
    """All model folder types supported by ComfyUI."""
    CHECKPOINTS = "checkpoints"
    DIFFUSION_MODELS = "diffusion_models"
    LORAS = "loras"
    VAE = "vae"
    TEXT_ENCODERS = "text_encoders"
    CLIP = "clip"
    CLIP_VISION = "clip_vision"
    CONTROLNET = "controlnet"
    EMBEDDINGS = "embeddings"
    UPSCALE_MODELS = "upscale_models"
    UNET = "unet"
    HYPERNETWORKS = "hypernetworks"
    STYLE_MODELS = "style_models"
    GLIGEN = "gligen"
    PHOTOMAKER = "photomaker"
    UNKNOWN = "unknown"


# ── Model family / architecture names ────────────────────────────────────────

class ModelFamily(str, Enum):
    """High-level model family for architecture-specific handling."""
    SD15 = "sd15"
    SD2 = "sd2"
    SDXL = "sdxl"
    FLUX = "flux"
    AURAFLOW = "auraflow"
    HUNYUAN = "hunyuan"
    WAN = "wan"
    PIXART = "pixart"
    QWEN = "qwen"
    UNKNOWN = "unknown"


# ── Backup item types ─────────────────────────────────────────────────────────

class BackupItem(str, Enum):
    """Things that can be backed up."""
    OUTPUTS = "outputs"
    INPUTS = "inputs"
    WORKFLOWS = "workflows"
    USER = "user"
    MODELS = "models"
    CUSTOM_NODES = "custom_nodes"


# ── Log levels ───────────────────────────────────────────────────────────────

class LogLevel(str, Enum):
    """Logging level names."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ── URL / filename patterns for model type detection ─────────────────────────

# Ordered list of (keyword_tuple, ModelType) — first match wins.
MODEL_TYPE_PATTERNS: list[tuple[tuple[str, ...], ModelType]] = [
    # Flux family
    (("flux", "f1"), ModelType.DIFFUSION_MODELS),
    # LoRA / LyCORIS
    (("lora", "lycoris", "locon", "loha"), ModelType.LORAS),
    # VAE
    (("vae",), ModelType.VAE),
    # ControlNet
    (("controlnet", "control_net", "control-net"), ModelType.CONTROLNET),
    # CLIP / text encoders
    (("clip_vision",), ModelType.CLIP_VISION),
    (("text_encoder", "t5", "clip_l", "clip_g"), ModelType.TEXT_ENCODERS),
    (("clip",), ModelType.CLIP),
    # Upscale
    (("upscale", "esrgan", "realesrgan", "swinir"), ModelType.UPSCALE_MODELS),
    # Embeddings
    (("embedding", "textual_inversion"), ModelType.EMBEDDINGS),
    # UNet
    (("unet",), ModelType.UNET),
    # Checkpoints (catch-all for .safetensors / .ckpt)
    (("checkpoint", "model", ".ckpt", ".safetensors"), ModelType.CHECKPOINTS),
]

# File extensions recognised as model files
MODEL_EXTENSIONS: frozenset[str] = frozenset({
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".bin",
    ".gguf",
    ".pkl",
})

# ── Well-known ComfyUI custom nodes ──────────────────────────────────────────

WELL_KNOWN_NODES: dict[str, str] = {
    "ComfyUI Manager": "https://github.com/ltdrdata/ComfyUI-Manager.git",
    "Impact Pack": "https://github.com/ltdrdata/ComfyUI-Impact-Pack.git",
    "Efficiency Nodes": "https://github.com/jags111/efficiency-nodes-comfyui.git",
    "ControlNet Aux": "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
    "Image Saver": "https://github.com/alexopus/ComfyUI-Image-Saver.git",
    "WAS Suite": "https://github.com/WASasquatch/was-node-suite-comfyui.git",
    "IPAdapter Plus": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
    "Ultimate SD Upscale": "https://github.com/ssitu/ComfyUI_UltimateSDUpscale.git",
    "Segment Anything": "https://github.com/storyicon/comfyui_segment_anything.git",
    "AnimateDiff": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git",
    "Video Helper": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
    "Prompt Styler": "https://github.com/twri/sdxl_prompt_styler.git",
    "Inpaint Crop": "https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch.git",
}

# ── HuggingFace URL patterns ──────────────────────────────────────────────────

HF_URL_PATTERNS: tuple[str, ...] = (
    "huggingface.co",
    "hf.co",
)

# ── CivitAI URL patterns ──────────────────────────────────────────────────────

CIVITAI_URL_PATTERNS: tuple[str, ...] = (
    "civitai.com",
)

# ── GitHub URL patterns ───────────────────────────────────────────────────────

GITHUB_URL_PATTERNS: tuple[str, ...] = (
    "github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
)

# ── ANSI colors (for raw terminals without Rich) ──────────────────────────────

class Color(str, Enum):
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


# ── Sentinel ──────────────────────────────────────────────────────────────────

class _Missing(Enum):
    """Sentinel for missing / unset config values."""
    MISSING = auto()


MISSING = _Missing.MISSING
