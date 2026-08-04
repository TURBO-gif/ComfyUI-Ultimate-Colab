import platform
import psutil


def print_system():

    print("=" * 40)

    print("SYSTEM")

    print("=" * 40)

    print("Platform :", platform.platform())

    print("CPU :", platform.processor())

    print("RAM :", round(psutil.virtual_memory().total / 1024**3, 2), "GB")
