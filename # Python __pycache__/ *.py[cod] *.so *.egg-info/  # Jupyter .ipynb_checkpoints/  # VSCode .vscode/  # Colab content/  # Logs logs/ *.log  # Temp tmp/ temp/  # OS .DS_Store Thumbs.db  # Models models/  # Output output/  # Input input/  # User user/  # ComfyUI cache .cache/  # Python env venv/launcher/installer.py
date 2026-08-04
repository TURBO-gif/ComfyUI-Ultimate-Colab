import os
import subprocess

COMFY_DIR = "/content/ComfyUI"

REPO = "https://github.com/comfyanonymous/ComfyUI.git"


def install():

    if not os.path.exists(COMFY_DIR):

        subprocess.run(
            [
                "git",
                "clone",
                REPO,
                COMFY_DIR,
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
