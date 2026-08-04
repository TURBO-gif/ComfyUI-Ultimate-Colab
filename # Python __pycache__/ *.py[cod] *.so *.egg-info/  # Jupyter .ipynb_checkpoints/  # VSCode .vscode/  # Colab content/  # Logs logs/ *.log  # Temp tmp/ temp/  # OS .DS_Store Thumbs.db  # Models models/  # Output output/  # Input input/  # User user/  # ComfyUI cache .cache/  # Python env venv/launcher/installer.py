import os

from .utils import run


def install():

    if os.path.exists("/content/ComfyUI"):

        print("ComfyUI already installed")

        return

    run(
        "git clone https://github.com/comfyanonymous/ComfyUI.git /content/ComfyUI"
    )

    run("pip install -r /content/ComfyUI/requirements.txt")
