import os
import subprocess

COMFY_DIR = "/content/ComfyUI"


def update():

    if not os.path.exists(COMFY_DIR):
        return

    subprocess.run(
        [
            "git",
            "-C",
            COMFY_DIR,
            "pull",
        ],
        check=True,
    )

    subprocess.run(
        [
            "pip",
            "install",
            "-r",
            f"{COMFY_DIR}/requirements.txt",
        ],
        check=True,
    )
