<div align="center">

# 🚀 ComfyUI Ultimate Colab

**The most powerful, production-quality Google Colab launcher for ComfyUI**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/TURBO-gif/ComfyUI-Ultimate-Colab/blob/main/ComfyUI_Ultimate_Colab.ipynb)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/TURBO-gif/ComfyUI-Ultimate-Colab/workflows/CI/badge.svg)](https://github.com/TURBO-gif/ComfyUI-Ultimate-Colab/actions)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔧 **Auto Install** | One-click install and update of ComfyUI |
| 📦 **Custom Nodes** | Auto-install ComfyUI Manager, Impact Pack, Efficiency Nodes and more |
| ⬇️ **Model Downloader** | Download from HuggingFace, CivitAI, GitHub Releases, Direct URLs |
| 🔍 **Smart Detection** | Automatically detects model type and places into the correct folder |
| 💾 **Google Drive** | Full integration — models, outputs, workflows saved to Drive |
| 🌐 **Tunnel Support** | Cloudflare, Pinggy, LocalTunnel — with auto-restart |
| 📊 **Rich Dashboard** | Live GPU/VRAM/RAM/disk metrics with model/node inventory |
| 🔒 **Backup & Restore** | Auto backup of outputs, workflows, models, nodes |
| 🔄 **Workflow Manager** | Save, load, export, import workflows |
| ⚡ **GPU Support** | Tesla T4, L4, A100 — auto-detected and optimized |
| 📝 **Full Logging** | Rotating file logs + rich console output |
| 🖥️ **CLI** | Full command-line interface for all operations |

---

## 🎯 Supported Models

- **Stable Diffusion 1.5 / 2.x**
- **SDXL** and SDXL Turbo
- **Flux** (Dev, Schnell, Pro)
- **AuraFlow**
- **Hunyuan DiT**
- **Wan**
- **PixArt** (Alpha, Sigma)
- **Qwen Image**
- **Z Image**
- Any model supported by ComfyUI

---

## 🚀 Quick Start

### Google Colab (Recommended)

1. Click the **Open in Colab** badge above
2. Connect to a GPU runtime (T4, L4, or A100)
3. Run all cells from top to bottom
4. Access ComfyUI via the Cloudflare tunnel URL

### Local Installation

```bash
git clone https://github.com/TURBO-gif/ComfyUI-Ultimate-Colab.git
cd ComfyUI-Ultimate-Colab
pip install -r requirements.txt
python -m comfy_launcher install
python -m comfy_launcher launch
```

---

## 📂 Directory Structure

```
ComfyUI-Ultimate-Colab/
├── README.md
├── LICENSE
├── requirements.txt
├── config.json                  # Main configuration
├── pyproject.toml               # Project metadata + tool config
├── .gitignore
├── ComfyUI_Ultimate_Colab.ipynb # Colab notebook (orchestrator only)
│
├── comfy_launcher/              # Main Python package
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── constants.py             # All constants / enums
│   ├── paths.py                 # Path resolution helpers
│   ├── installer.py             # ComfyUI install/update logic
│   ├── updater.py               # Auto-updater
│   ├── launcher.py              # Process launcher
│   ├── drive.py                 # Google Drive integration
│   ├── tunnel.py                # Tunnel management
│   ├── dashboard.py             # Rich dashboard
│   ├── logger.py                # Logging setup
│   ├── downloader.py            # Core download engine
│   ├── civitai.py               # CivitAI API client
│   ├── huggingface.py           # HuggingFace integration
│   ├── github.py                # GitHub releases downloader
│   ├── model_manager.py         # Model registry & management
│   ├── node_manager.py          # Custom node management
│   ├── workflow.py              # Workflow manager
│   ├── backup.py                # Backup & restore
│   ├── gpu.py                   # GPU detection & optimization
│   ├── system.py                # System information
│   ├── cli.py                   # CLI interface
│   └── utils.py                 # Shared utilities
│
├── docs/
│   ├── installation.md
│   ├── usage.md
│   ├── api.md
│   ├── architecture.md
│   ├── faq.md
│   └── troubleshooting.md
│
├── examples/
│   ├── download_flux.py
│   ├── download_sdxl.py
│   └── custom_workflow.py
│
├── assets/
│   └── banner.png
│
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_downloader.py
    ├── test_model_manager.py
    ├── test_node_manager.py
    ├── test_backup.py
    ├── test_gpu.py
    ├── test_system.py
    └── test_utils.py
```

---

## ⚙️ Configuration

All configuration lives in `config.json` at the project root. You can override any setting:

```json
{
  "comfyui_dir": "/content/ComfyUI",
  "drive_root": "/content/drive/MyDrive/AI/ComfyUI",
  "tunnel": {
    "provider": "cloudflare",
    "port": 8188
  },
  "models": {
    "auto_detect": true,
    "verify_sha256": true
  }
}
```

See [docs/usage.md](docs/usage.md) for a full configuration reference.

---

## 🖥️ CLI Reference

```bash
# Install / update ComfyUI
python -m comfy_launcher install
python -m comfy_launcher update

# Launch ComfyUI
python -m comfy_launcher launch [--port 8188] [--no-tunnel]

# Download a model
python -m comfy_launcher download <url> [--type lora] [--verify]

# Manage nodes
python -m comfy_launcher nodes install <url>
python -m comfy_launcher nodes update

# Backup / restore
python -m comfy_launcher backup [--include models]
python -m comfy_launcher restore <backup_id>

# Show dashboard
python -m comfy_launcher dashboard

# Show status
python -m comfy_launcher status
```

---

## 📋 Requirements

- Python 3.12+
- CUDA-capable GPU (for local use)
- Google Colab (for cloud use)
- Google Drive (optional, for persistence)

---

## 🤝 Contributing

Pull requests are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and make sure all tests pass.

```bash
pip install -e ".[dev]"
black .
ruff check .
pytest tests/ -v
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) by comfyanonymous
- [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) by ltdrdata
- [Rich](https://github.com/Textualize/rich) for the beautiful terminal UI
- The entire ComfyUI community

