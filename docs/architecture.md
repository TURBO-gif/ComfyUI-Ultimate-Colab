# Architecture

## Overview

ComfyUI Ultimate Colab follows a **modular, layered architecture** where the Jupyter notebook is a pure orchestrator and all business logic lives in the `comfy_launcher` Python package.

```
┌─────────────────────────────────────────────────────────┐
│                 Notebook / CLI / User Code               │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    comfy_launcher                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  config.py   │  │   paths.py   │  │   logger.py   │  │
│  │  constants   │  │              │  │               │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────┘  │
│         │                 │                              │
│  ┌──────▼─────────────────▼──────────────────────────┐  │
│  │                  Core Managers                     │  │
│  │  installer  updater  launcher  drive  tunnel       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │               Download Layer                     │    │
│  │  downloader  huggingface  civitai  github        │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │               Feature Managers                   │    │
│  │  model_manager  node_manager  backup  workflow   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │               Monitoring & UI                    │    │
│  │  dashboard  gpu  system                          │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │                  CLI (cli.py)                    │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Module Responsibilities

### Foundation Layer

| Module | Purpose |
|---|---|
| `config.py` | Load, validate, and provide dotted-key access to `config.json` |
| `constants.py` | All enums, string constants, URL patterns, model type mappings |
| `paths.py` | Resolve every path from config — no hardcoded paths elsewhere |
| `logger.py` | Rich console + rotating file handler setup |
| `utils.py` | Shared helpers: hashing, process running, retry decorator |

### Core Managers

| Module | Purpose |
|---|---|
| `installer.py` | Clone ComfyUI, install requirements |
| `updater.py` | Git pull ComfyUI and all custom nodes |
| `launcher.py` | Start/stop ComfyUI process with GPU-aware arguments |
| `drive.py` | Mount Drive, create directories, symlink into ComfyUI |
| `tunnel.py` | Cloudflare / Pinggy / LocalTunnel management |

### Download Layer

| Module | Purpose |
|---|---|
| `downloader.py` | Resumable core downloader with SHA-256, progress bars, async |
| `huggingface.py` | HuggingFace Hub client; hub library + direct fallback |
| `civitai.py` | CivitAI API v1; model metadata + download URL resolution |
| `github.py` | GitHub Releases API; asset resolution + download |

### Feature Managers

| Module | Purpose |
|---|---|
| `model_manager.py` | Auto-detect type, route to correct source, disk registry |
| `node_manager.py` | Install/update/list custom nodes, requirements install |
| `backup.py` | tar.gz archives with manifest JSON, auto-prune |
| `workflow.py` | Save/load/export/import workflows with metadata |

### Monitoring

| Module | Purpose |
|---|---|
| `gpu.py` | Detect GPU via PyTorch → nvidia-smi, compute launch args |
| `system.py` | CPU/RAM/disk via psutil |
| `dashboard.py` | Rich live panels combining all info |

---

## Key Design Decisions

### 1. Config-Driven Paths
All paths are resolved through `PathResolver` from `config.json`. No `Path("/content/...")` strings exist outside `config.py` defaults.

### 2. Source Detection Is Automatic
`detect_source()` and `detect_model_type()` in `model_manager.py` inspect URLs and filenames. Users never need to specify where a model goes.

### 3. Download Is Resumable
`Downloader._download_with_resume()` sends `Range: bytes={existing}-` when a partial file exists. This handles interrupted downloads transparently.

### 4. Drive Symlinking
Instead of copying models to ComfyUI on each session, Drive directories are symlinked into the ComfyUI directory. Reads and writes go directly to Drive.

### 5. Modular Tunnel Support
`TunnelManager` dispatches to provider-specific methods. Adding a new tunnel only requires a new `_start_<provider>()` method.

### 6. Registry Pattern
Both `ModelManager` and `NodeManager` maintain a JSON registry (`.model_registry.json`, `.node_registry.json`) inside ComfyUI. This enables fast inventory queries without rescanning the filesystem every time.
