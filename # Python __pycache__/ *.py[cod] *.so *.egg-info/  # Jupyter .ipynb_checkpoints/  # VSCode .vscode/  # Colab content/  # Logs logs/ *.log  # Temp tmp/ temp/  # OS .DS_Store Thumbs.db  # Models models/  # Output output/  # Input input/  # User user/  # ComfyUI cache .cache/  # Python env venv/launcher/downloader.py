from pathlib import Path
import subprocess

MODELS = {
    "checkpoints": "models/checkpoints",
    "vae": "models/vae",
    "loras": "models/loras",
    "diffusion_models": "models/diffusion_models",
    "text_encoders": "models/text_encoders",
}


def ensure_folder(folder):
    Path(folder).mkdir(parents=True, exist_ok=True)


def download(url, output):

    ensure_folder(Path(output).parent)

    cmd = [
        "wget",
        "-c",
        "-O",
        output,
        url,
    ]

    subprocess.run(cmd, check=True)
