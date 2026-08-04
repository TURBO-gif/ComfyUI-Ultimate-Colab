"""
tests/test_system.py — Unit tests for system information.
"""

from __future__ import annotations

import pytest

from comfy_launcher.system import SystemInfo, get_system_info


class TestGetSystemInfo:
    def test_returns_system_info(self) -> None:
        info = get_system_info()
        assert isinstance(info, SystemInfo)

    def test_python_version_not_empty(self) -> None:
        info = get_system_info()
        assert info.python_ver != ""
        assert "." in info.python_ver

    def test_cpu_cores_positive(self) -> None:
        info = get_system_info()
        assert info.cpu_cores >= 1

    def test_ram_total_positive(self) -> None:
        info = get_system_info()
        assert info.ram_total_mb > 0

    def test_ram_used_lte_total(self) -> None:
        info = get_system_info()
        assert info.ram_used_mb <= info.ram_total_mb

    def test_disk_total_positive(self) -> None:
        info = get_system_info()
        assert info.disk_total_gb > 0


class TestSystemInfoProperties:
    def _make(self, **kwargs) -> SystemInfo:
        defaults = {
            "os_name": "Linux",
            "os_version": "5.15.0",
            "python_ver": "3.12.0",
            "cpu_cores": 4,
            "cpu_threads": 8,
            "ram_total_mb": 16384,
            "ram_used_mb": 8192,
            "ram_free_mb": 8192,
            "disk_total_gb": 100.0,
            "disk_used_gb": 40.0,
            "disk_free_gb": 60.0,
            "disk_path": "/",
        }
        defaults.update(kwargs)
        return SystemInfo(**defaults)

    def test_ram_used_pct(self) -> None:
        info = self._make(ram_total_mb=16384, ram_used_mb=8192)
        assert abs(info.ram_used_pct - 50.0) < 0.1

    def test_disk_used_pct(self) -> None:
        info = self._make(disk_total_gb=100.0, disk_used_gb=75.0)
        assert abs(info.disk_used_pct - 75.0) < 0.1

    def test_zero_ram_total(self) -> None:
        info = self._make(ram_total_mb=0, ram_used_mb=0)
        assert info.ram_used_pct == 0.0
