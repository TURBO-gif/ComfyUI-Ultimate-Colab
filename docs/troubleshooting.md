# Troubleshooting Guide

## Diagnostic Steps

Always start by checking:
1. `python -m comfy_launcher status` — shows GPU, disk, ComfyUI version
2. Check logs: `cat /content/drive/MyDrive/AI/ComfyUI/logs/comfy_launcher.log`
3. Run with debug logging: `COMFY_LOGGING__LEVEL=DEBUG python -m comfy_launcher launch`

---

## Common Issues

### ComfyUI won't start

**Symptom**: Launcher exits immediately or hangs.

**Check**:
```bash
python -m comfy_launcher status
# Look for: Installed: True
```

**Fix**:
```bash
python -m comfy_launcher install --force  # Reclone ComfyUI
```

---

### CUDA out of memory (OOM)

**Symptom**: `RuntimeError: CUDA out of memory` in ComfyUI logs.

**Fix options**:
- Add `--lowvram` to `comfyui.extra_args` in config.json
- Use `--medvram` as intermediate option
- Reduce batch size in workflow
- Use smaller model (e.g., SDXL Turbo instead of SDXL base)

---

### Google Drive not mounting

**Symptom**: `DriveManager: Drive not mounted — cannot link models`

**Check**:
- Only works inside Google Colab
- Re-run the Mount Drive cell
- Ensure `drive.enabled` is `true` in config

**Manual mount**:
```python
from google.colab import drive
drive.mount('/content/drive', force_remount=True)
```

---

### Download fails / slow

**Symptom**: Download times out or produces corrupted file.

**Fix**:
```bash
# Retry with explicit progress
python -m comfy_launcher download <url>

# Disable SHA256 check (temp)
python -m comfy_launcher download <url> --no-verify

# Check CivitAI API key
echo $CIVITAI_API_KEY
```

---

### Cloudflare tunnel URL not appearing

**Symptom**: No URL printed after starting.

**Fix**:
1. Wait up to 60 seconds for Cloudflare to assign a URL
2. Try a different provider: `--tunnel-provider pinggy`
3. Check if `cloudflared` binary is executable:
```bash
ls -la /content/cloudflared
chmod +x /content/cloudflared
```

---

### Custom node import error

**Symptom**: ComfyUI prints import errors for a node.

**Fix**:
```bash
# Reinstall node requirements
cd /content/ComfyUI/custom_nodes/<NodeName>
pip install -r requirements.txt

# Or update the node
python -m comfy_launcher nodes update
```

---

### Disk space issues

**Check available space**:
```bash
df -h /content
```

**Free space**:
```bash
# Remove pip cache
pip cache purge

# Clear ComfyUI output
python -m comfy_launcher backup --include outputs
rm -rf /content/ComfyUI/output/*

# Nuclear option: remove ComfyUI (models remain on Drive)
python -m comfy_launcher clean --yes
```

---

## Log Files

| Log File | Location |
|---|---|
| Launcher log | `<drive_root>/logs/comfy_launcher.log` |
| ComfyUI log | Streamed to launcher log under `[ComfyUI]` prefix |

Enable debug mode:
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

---

## Getting Help

1. Check [FAQ](faq.md) first
2. Search [GitHub Issues](https://github.com/TURBO-gif/ComfyUI-Ultimate-Colab/issues)
3. Open a new issue with:
   - Your GPU type
   - Error message / stack trace
   - Output of `python -m comfy_launcher status`
