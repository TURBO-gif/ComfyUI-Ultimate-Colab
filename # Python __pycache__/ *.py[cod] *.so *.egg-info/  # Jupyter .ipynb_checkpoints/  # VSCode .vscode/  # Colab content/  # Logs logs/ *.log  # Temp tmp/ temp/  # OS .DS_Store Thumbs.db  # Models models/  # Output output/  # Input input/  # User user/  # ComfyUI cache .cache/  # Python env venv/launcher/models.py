from pathlib import Path


def list_models(root):

    root = Path(root)

    for file in root.rglob("*.safetensors"):

        print(file)
