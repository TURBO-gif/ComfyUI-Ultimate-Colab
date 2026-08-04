from pathlib import Path


def backup(workflow, backup_folder):

    Path(backup_folder).mkdir(
        parents=True,
        exist_ok=True,
    )

    Path(workflow).rename(
        Path(backup_folder) / Path(workflow).name
    )
