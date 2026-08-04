# API Reference

## comfy_launcher.config

### `Config`

```python
class Config(config_path=None, overrides=None)
```

**Methods**:
- `get(dotted_key, default=None)` — Get a value by dotted path
- `set(dotted_key, value)` — Set a value at runtime
- `save(path=None)` — Persist config to disk
- `as_dict()` — Return deep copy of config dict

**Properties**: `comfyui_dir`, `comfyui_port`, `drive_root`, `tunnel_provider`, `civitai_api_key`, `hf_token`, `log_level`, `model_dirs`, `verify_sha256`, `resume_downloads`

---

## comfy_launcher.model_manager

### `ModelManager`

```python
class ModelManager(cfg: Config, paths: PathResolver)
```

**Methods**:
- `download(url, model_type=None, dest_dir=None, filename=None, show_progress=True) → Path`
- `download_batch(entries: list[dict]) → list[Path]`
- `scan_disk() → list[ModelRecord]`
- `list_installed() → list[ModelRecord]`
- `print_inventory()` — Print Rich table

### `detect_model_type(url, filename=None) → ModelType`

Auto-detect model type from URL and filename.

### `detect_source(url) → DownloadSource`

Detect download source (HuggingFace, CivitAI, GitHub, Direct).

---

## comfy_launcher.node_manager

### `NodeManager`

```python
class NodeManager(cfg: Config, paths: PathResolver)
```

**Methods**:
- `install(url, name=None) → Path`
- `install_defaults()` — Install nodes from config
- `install_by_name(name) → Optional[Path]`
- `scan_disk() → list[NodeRecord]`
- `print_inventory()`

---

## comfy_launcher.backup

### `BackupManager`

```python
class BackupManager(cfg: Config, paths: PathResolver)
```

**Methods**:
- `create(includes=None, description="", compress=None) → BackupManifest`
- `restore(backup_id, items=None, overwrite=True)`
- `list_backups() → list[BackupManifest]`
- `print_list()`

---

## comfy_launcher.workflow

### `WorkflowManager`

```python
class WorkflowManager(cfg: Config, paths: PathResolver)
```

**Methods**:
- `save(workflow, name, description="", tags=None) → Path`
- `load(name_or_path) → dict`
- `delete(name_or_path)`
- `export(name_or_path, dest) → Path`
- `import_workflow(src, name=None) → Path`
- `list_workflows() → list[WorkflowRecord]`
- `print_list()`

---

## comfy_launcher.gpu

### `detect_gpu() → GPUInfo`

Detect current GPU using PyTorch (primary) or nvidia-smi (fallback).

### `get_comfyui_launch_args(gpu_info: GPUInfo) → list[str]`

Return recommended ComfyUI launch arguments for the detected GPU.

### `GPUInfo`

| Attribute | Type | Description |
|---|---|---|
| `available` | `bool` | Whether CUDA is available |
| `name` | `str` | GPU model name |
| `gpu_type` | `GPUType` | Classified GPU type |
| `vram_total_mb` | `int` | Total VRAM in MB |
| `vram_used_mb` | `int` | Used VRAM in MB |
| `cuda_version` | `str` | CUDA version |
| `vram_total_gb` | `float` | Total VRAM in GB (property) |
| `vram_used_pct` | `float` | VRAM usage % (property) |

---

## comfy_launcher.tunnel

### `TunnelManager`

```python
class TunnelManager(cfg: Config, paths: PathResolver)
```

**Methods**:
- `start(provider=None, port=None) → Optional[str]` — Returns tunnel URL
- `stop()`
- `restart() → Optional[str]`

**Properties**: `current`, `is_running`

---

## comfy_launcher.downloader

### `Downloader`

```python
class Downloader(
    chunk_size=4MB,
    max_retries=3,
    retry_delay=3.0,
    verify_sha256=True,
    headers=None
)
```

**Methods**:
- `download(url, dest, expected_sha256=None, progress=True, filename=None) → DownloadResult`
- `download_many(tasks, progress=True) → list[DownloadResult]`
- `download_async(url, dest, session=None) → DownloadResult` *(async)*
- `download_many_async(tasks, concurrency=3) → list[DownloadResult]` *(async)*

---

## comfy_launcher.constants

### Enumerations

- `GPUType` — TESLA_T4, L4, A100, RTX_3090, RTX_4090, …
- `TunnelProvider` — CLOUDFLARE, PINGGY, LOCALTUNNEL
- `DownloadSource` — HUGGINGFACE, CIVITAI, GITHUB, DIRECT
- `ModelType` — CHECKPOINTS, LORAS, VAE, CONTROLNET, …
- `ModelFamily` — SD15, SDXL, FLUX, AURAFLOW, …
- `BackupItem` — OUTPUTS, INPUTS, WORKFLOWS, USER, MODELS, CUSTOM_NODES

### Constants

- `MODEL_TYPE_PATTERNS` — URL keyword → ModelType mapping
- `MODEL_EXTENSIONS` — Set of recognised model file extensions
- `WELL_KNOWN_NODES` — Name → GitHub URL mapping for popular nodes
- `HF_URL_PATTERNS`, `CIVITAI_URL_PATTERNS`, `GITHUB_URL_PATTERNS`
