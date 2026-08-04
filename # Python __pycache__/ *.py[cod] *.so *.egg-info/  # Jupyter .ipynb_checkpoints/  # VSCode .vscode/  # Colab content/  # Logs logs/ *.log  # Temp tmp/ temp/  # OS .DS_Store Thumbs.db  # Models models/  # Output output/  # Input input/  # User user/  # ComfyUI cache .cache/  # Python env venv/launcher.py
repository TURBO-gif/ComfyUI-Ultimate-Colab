#!/usr/bin/env python3

import argparse

from launcher.installer import install
from launcher.dashboard import show
from launcher.drive import mount
from launcher.gpu import gpu_info
from launcher.system import print_system


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=[
            "install",
            "dashboard",
            "gpu",
            "drive",
        ],
    )

    args = parser.parse_args()

    if args.command == "install":
        install()

    elif args.command == "dashboard":
        show()

    elif args.command == "gpu":
        gpu_info()

    elif args.command == "drive":
        mount()


if __name__ == "__main__":
    main()
