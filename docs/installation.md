# Installation Guide

## Google Colab (Recommended)

### Step 1 — Open the Notebook

Click the **Open in Colab** badge in the README, or open:
```
https://colab.research.google.com/github/TURBO-gif/ComfyUI-Ultimate-Colab/blob/main/ComfyUI_Ultimate_Colab.ipynb
```

### Step 2 — Select a GPU Runtime

1. **Runtime** → **Change runtime type**
2. Select **GPU** (T4 recommended for free tier)
3. Click **Save**

### Step 3 — Run the Notebook

Click **Runtime → Run all** and wait for setup to complete.

---

## Local Installation

### Requirements

- Python 3.12+
- CUDA-capable GPU (recommended)
- Git

### Steps

```bash
# Clone the project
git clone https://github.com/TURBO-gif/ComfyUI-Ultimate-Colab.git
cd ComfyUI-Ultimate-Colab

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"  # Development mode with all extras

# Install and launch ComfyUI
python -m comfy_launcher install
python -m comfy_launcher launch
```

---

## Google Drive Setup (optional but recommended)

When running in Colab, Google Drive is automatically mounted. The following directory structure is created:

```
MyDrive/
└── AI/
    └── ComfyUI/
        ├── ComfyUI/
        │   ├── models/
        │   │   ├── checkpoints/
        │   │   ├── loras/
        │   │   ├── vae/
        │   │   └── ...
        │   ├── input/
        │   ├── output/
        │   └── user/
        ├── workflows/
        ├── custom_nodes/
        ├── downloads/
        ├── logs/
        ├── backups/
        └── config/
```

All model files placed in these Drive folders persist across Colab sessions.

---

## Configuration

Copy the default config and customise:

```bash
cp config.json config.local.json
```

Add `.local.json` overrides (these are gitignored):

```json
{
  "civitai": {
    "api_key": "your_civitai_api_key_here"
  },
  "huggingface": {
    "token": "hf_your_token_here"
  }
}
```

---

## API Keys

| Service | Where to Get | Environment Variable |
|---|---|---|
| CivitAI | [civitai.com/user/account](https://civitai.com/user/account) | `CIVITAI_API_KEY` |
| HuggingFace | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | `HF_TOKEN` |

You can set these in Google Colab Secrets (🔑 key icon in the left sidebar).
