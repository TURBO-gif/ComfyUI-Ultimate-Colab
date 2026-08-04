import json

from pathlib import Path


CONFIG = Path("config.json")


def load():

    with open(CONFIG) as f:

        return json.load(f)
