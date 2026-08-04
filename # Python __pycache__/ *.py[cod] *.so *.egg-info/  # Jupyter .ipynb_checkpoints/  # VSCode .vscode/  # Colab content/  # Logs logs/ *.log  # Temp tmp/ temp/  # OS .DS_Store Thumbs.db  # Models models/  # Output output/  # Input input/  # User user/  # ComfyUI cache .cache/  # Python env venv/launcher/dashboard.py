import psutil
import shutil
import subprocess


def show():

    print("=" * 60)

    print("ComfyUI Ultimate Colab")

    print("=" * 60)

    print(
        "RAM:",
        round(
            psutil.virtual_memory().total / 1024**3,
            2,
        ),
        "GB",
    )

    total, used, free = shutil.disk_usage("/")

    print(
        "Disk:",
        round(
            free / 1024**3,
            2,
        ),
        "GB Free",
    )

    try:

        subprocess.run(
            ["nvidia-smi"],
            check=False,
        )

    except Exception:

        print("GPU unavailable")
