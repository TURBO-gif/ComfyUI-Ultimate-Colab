"""
examples/custom_workflow.py — Example: Save and load a custom workflow.
"""

from __future__ import annotations

from comfy_launcher.config import get_config
from comfy_launcher.logger import setup_logging
from comfy_launcher.paths import get_paths
from comfy_launcher.workflow import WorkflowManager

cfg = get_config()
setup_logging()
paths = get_paths(cfg)
wf_mgr = WorkflowManager(cfg, paths)

# Example workflow dict (simplified ComfyUI format)
my_workflow = {
    "1": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "flux1-dev.safetensors"}
    },
    "2": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "A beautiful sunset over the ocean", "clip": ["1", 1]}
    },
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["2", 0],
            "negative": ["4", 0],
            "latent_image": ["5", 0],
            "seed": 42,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
        }
    },
}

# Save the workflow
saved_path = wf_mgr.save(
    my_workflow,
    name="Flux Sunset Example",
    description="Simple Flux text-to-image workflow",
    tags=["flux", "landscape"],
)
print(f"Saved to: {saved_path}")

# Load it back
loaded = wf_mgr.load("Flux Sunset Example")
print(f"Loaded nodes: {list(loaded.keys())}")

# List all workflows
wf_mgr.print_list()
