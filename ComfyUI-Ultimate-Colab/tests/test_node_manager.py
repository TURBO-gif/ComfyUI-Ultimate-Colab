"""
tests/test_node_manager.py — Unit tests for NodeManager.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from comfy_launcher.node_manager import NodeManager, NodeRecord


class TestNodeManagerScanDisk:
    def test_empty_dir(self, cfg, paths) -> None:
        nodes_dir = paths.comfyui_custom_nodes_dir
        nodes_dir.mkdir(parents=True, exist_ok=True)
        mgr = NodeManager(cfg, paths)
        assert mgr.scan_disk() == []

    def test_finds_node_directories(self, cfg, paths) -> None:
        nodes_dir = paths.comfyui_custom_nodes_dir
        node_dir = nodes_dir / "MyNode"
        node_dir.mkdir(parents=True, exist_ok=True)
        (node_dir / "__init__.py").write_text("")

        mgr = NodeManager(cfg, paths)
        records = mgr.scan_disk()
        names = [r.name for r in records]
        assert "MyNode" in names

    def test_ignores_files(self, cfg, paths) -> None:
        nodes_dir = paths.comfyui_custom_nodes_dir
        nodes_dir.mkdir(parents=True, exist_ok=True)
        (nodes_dir / "some_file.txt").write_text("hello")

        mgr = NodeManager(cfg, paths)
        records = mgr.scan_disk()
        names = [r.name for r in records]
        assert "some_file.txt" not in names


class TestNodeRecord:
    def test_default_enabled(self) -> None:
        rec = NodeRecord(name="TestNode", path="/tmp/nodes/TestNode")
        assert rec.enabled is True

    def test_installed_at_set(self) -> None:
        rec = NodeRecord(name="TestNode", path="/tmp/nodes/TestNode")
        assert rec.installed_at != ""
