"""
tests/test_backup.py — Unit tests for BackupManager.
"""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from comfy_launcher.backup import BackupManager


@pytest.fixture
def backup_mgr(cfg, paths, tmp_path):
    # Create some fake content to back up
    output_dir = paths.comfyui_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "image_001.png").write_bytes(b"\x89PNG" + b"\x00" * 100)

    input_dir = paths.comfyui_input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "sample.png").write_bytes(b"\x89PNG" + b"\x00" * 50)

    return BackupManager(cfg, paths)


class TestBackupCreate:
    def test_creates_archive(self, backup_mgr: BackupManager, tmp_path: Path) -> None:
        manifest = backup_mgr.create(includes=["outputs"])
        backup_dir = backup_mgr.backup_dir

        # Find the archive
        archives = list(backup_dir.glob(f"{manifest.id}.*"))
        assert len(archives) == 1

    def test_manifest_written(self, backup_mgr: BackupManager) -> None:
        manifest = backup_mgr.create(includes=["outputs"])
        mf_path = backup_mgr.backup_dir / f"{manifest.id}.manifest.json"
        assert mf_path.exists()

    def test_manifest_contains_includes(self, backup_mgr: BackupManager) -> None:
        manifest = backup_mgr.create(includes=["outputs", "inputs"])
        assert "outputs" in manifest.includes
        assert "inputs" in manifest.includes

    def test_size_bytes_nonzero(self, backup_mgr: BackupManager) -> None:
        manifest = backup_mgr.create(includes=["outputs"])
        assert manifest.size_bytes > 0

    def test_list_backups(self, backup_mgr: BackupManager) -> None:
        backup_mgr.create(includes=["outputs"])
        backup_mgr.create(includes=["inputs"])
        backups = backup_mgr.list_backups()
        assert len(backups) >= 2

    def test_list_sorted_newest_first(self, backup_mgr: BackupManager) -> None:
        import time
        backup_mgr.create(includes=["outputs"])
        time.sleep(1)
        backup_mgr.create(includes=["inputs"])
        backups = backup_mgr.list_backups()
        assert backups[0].created_at >= backups[1].created_at


class TestBackupRestore:
    def test_restore_creates_files(self, backup_mgr: BackupManager, paths) -> None:
        manifest = backup_mgr.create(includes=["outputs"])

        # Remove original
        import shutil
        shutil.rmtree(paths.comfyui_output_dir)
        assert not paths.comfyui_output_dir.exists()

        backup_mgr.restore(manifest.id)
        assert paths.comfyui_output_dir.exists()

    def test_restore_bad_id_raises(self, backup_mgr: BackupManager) -> None:
        with pytest.raises(FileNotFoundError):
            backup_mgr.restore("nonexistent_backup_id")


class TestBackupPrune:
    def test_prune_respects_max_backups(self, backup_mgr: BackupManager) -> None:
        # Create 7 backups when max is 5
        import time
        for i in range(7):
            backup_mgr.create(includes=["outputs"])
            time.sleep(0.05)

        backups = backup_mgr.list_backups()
        assert len(backups) <= 5
