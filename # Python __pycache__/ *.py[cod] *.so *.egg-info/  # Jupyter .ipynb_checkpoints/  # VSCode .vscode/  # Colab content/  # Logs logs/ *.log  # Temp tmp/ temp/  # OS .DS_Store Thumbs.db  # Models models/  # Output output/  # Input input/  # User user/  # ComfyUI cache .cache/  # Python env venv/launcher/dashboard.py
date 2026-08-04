import shutil
import psutil


def show():

    print("=" * 50)

    print("SYSTEM")

    print("=" * 50)

    print(
        "RAM:",
        round(psutil.virtual_memory().total / 1024**3, 2),
        "GB",
    )

    total, used, free = shutil.disk_usage("/")

    print(
        "Disk:",
        round(free / 1024**3, 2),
        "GB free",
    )
