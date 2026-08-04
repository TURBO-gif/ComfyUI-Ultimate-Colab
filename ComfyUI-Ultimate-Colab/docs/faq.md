# FAQ — Frequently Asked Questions

## General

**Q: What GPUs are supported?**

A: All CUDA-capable NVIDIA GPUs. Best supported: Tesla T4 (Colab free), L4, A100.

**Q: Can I run this locally?**

A: Yes! Install with `pip install -e .` and run `python -m comfy_launcher launch`.

**Q: Do models persist between Colab sessions?**

A: Yes — when Google Drive is enabled, all models are symlinked to Drive and persist automatically.

---

## Models

**Q: Where do downloaded models go?**

A: The launcher auto-detects the model type and places it in the correct folder. Flux → `diffusion_models/`, LoRAs → `loras/`, etc.

**Q: How do I force a model into a specific folder?**

A: Use `--type`:
```bash
python -m comfy_launcher download <url> --type loras
```

**Q: Can I download from private HuggingFace repos?**

A: Yes. Set your HF token:
```bash
export HF_TOKEN=hf_your_token_here
```

**Q: How do I download from CivitAI?**

A: Set your API key in `config.json` or as `CIVITAI_API_KEY` env var. Then use any CivitAI model page URL.

---

## Tunnels

**Q: Why is the Cloudflare URL different every session?**

A: Cloudflare assigns random subdomains. For a persistent URL, use Pinggy with a token or LocalTunnel with a subdomain.

**Q: The tunnel URL doesn't work in my browser.**

A: Some countries block Cloudflare. Try `--tunnel-provider pinggy` instead.

**Q: Can I use my own ngrok/custom tunnel?**

A: Not yet built-in, but you can start your tunnel manually and skip `--tunnel` flag.

---

## Errors

**Q: `git.exc.GitCommandError: git clone failed`**

A: GitHub may be temporarily unavailable. Retry, or check your network. In Colab, ensure the session has internet access.

**Q: `RuntimeError: ComfyUI main.py not found`**

A: Run `python -m comfy_launcher install` first.

**Q: `OSError: [Errno 28] No space left on device`**

A: Colab disk is limited (~78 GB). Use `python -m comfy_launcher clean` to remove the ComfyUI installation and re-install, or use Google Drive for storage.

**Q: SHA-256 mismatch on download**

A: The file may have been corrupted in transit. Delete the partial file and retry. Disable with `--no-verify` as a last resort.

---

## Custom Nodes

**Q: A node fails to install requirements**

A: Some nodes require system packages (e.g., `libGL`). In Colab, run:
```python
!apt-get install -y libgl1-mesa-glx
```

**Q: How do I disable a node without uninstalling it?**

A: Rename the node folder to `_disabled_NodeName` — ComfyUI ignores folders starting with `_`.
