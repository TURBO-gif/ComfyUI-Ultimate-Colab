# Usage Guide

## Downloading Models

### From HuggingFace

```bash
# Download a specific file
python -m comfy_launcher download \
  "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors"

# The launcher automatically detects it's a Flux model
# and places it in models/diffusion_models/
```

### From CivitAI

```bash
# Download by model page URL
python -m comfy_launcher download "https://civitai.com/models/133005"

# Download a specific version
python -m comfy_launcher download \
  "https://civitai.com/models/133005?modelVersionId=357609"
```

### Override model type

```bash
python -m comfy_launcher download \
  "https://example.com/my_model.safetensors" \
  --type loras
```

### Available model types

| Type | Folder |
|---|---|
| `checkpoints` | models/checkpoints |
| `diffusion_models` | models/diffusion_models |
| `loras` | models/loras |
| `vae` | models/vae |
| `text_encoders` | models/text_encoders |
| `clip` | models/clip |
| `clip_vision` | models/clip_vision |
| `controlnet` | models/controlnet |
| `embeddings` | models/embeddings |
| `upscale_models` | models/upscale_models |
| `unet` | models/unet |

---

## Custom Nodes

### Install a node by URL

```bash
python -m comfy_launcher nodes install \
  "https://github.com/ltdrdata/ComfyUI-Manager.git"
```

### Install a well-known node by name

```bash
python -m comfy_launcher nodes install "ComfyUI Manager"
python -m comfy_launcher nodes install "Impact Pack"
python -m comfy_launcher nodes install "ControlNet Aux"
```

### List installed nodes

```bash
python -m comfy_launcher nodes list
```

### Update all nodes

```bash
python -m comfy_launcher nodes update
```

---

## Launching ComfyUI

```bash
# Default — starts on port 8188 with Cloudflare tunnel
python -m comfy_launcher launch

# Custom port
python -m comfy_launcher launch --port 9000

# Without tunnel (local-only)
python -m comfy_launcher launch --no-tunnel

# Use a different tunnel provider
python -m comfy_launcher launch --tunnel-provider pinggy
```

---

## Backup & Restore

### Create a backup

```bash
# Backup everything (configured via backup.include in config.json)
python -m comfy_launcher backup

# Backup specific items
python -m comfy_launcher backup --include outputs --include workflows

# With description
python -m comfy_launcher backup --description "Before updating nodes"
```

### List backups

```bash
python -m comfy_launcher restore --help
# (backups listed in the status command output)
```

### Restore from backup

```bash
python -m comfy_launcher restore 20240115_142300

# Restore only specific items
python -m comfy_launcher restore 20240115_142300 --items outputs --items workflows
```

---

## Dashboard

### One-time snapshot

```bash
python -m comfy_launcher dashboard
```

### Live auto-refresh

```bash
python -m comfy_launcher dashboard --live --refresh 3
```

---

## Configuration Reference

All settings in `config.json`:

| Key | Default | Description |
|---|---|---|
| `comfyui.port` | `8188` | ComfyUI server port |
| `comfyui.dir` | `/content/ComfyUI` | Installation directory |
| `tunnel.provider` | `cloudflare` | Tunnel provider |
| `models.verify_sha256` | `true` | Verify downloads |
| `models.resume_downloads` | `true` | Resume partial downloads |
| `backup.max_backups` | `10` | Max backups to keep |
| `backup.compress` | `true` | Gzip archives |
| `logging.level` | `INFO` | Log level |
| `civitai.api_key` | `null` | CivitAI API key |
| `huggingface.token` | `null` | HuggingFace token |

---

## Python API

```python
from comfy_launcher.config import Config
from comfy_launcher.model_manager import ModelManager
from comfy_launcher.paths import PathResolver

cfg = Config()
paths = PathResolver(cfg)
mgr = ModelManager(cfg, paths)

# Download a model
path = mgr.download("https://huggingface.co/...")

# List installed models
models = mgr.scan_disk()
for m in models:
    print(m.name, m.model_type, m.size_human)
```
