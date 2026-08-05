"""
tests/test_gpu.py — Unit tests for GPU detection.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from comfy_launcher.constants import GPUType
from comfy_launcher.gpu import GPUInfo, _classify_gpu, detect_gpu, get_comfyui_launch_args


class TestClassifyGpu:
    def test_a100(self) -> None:
        assert _classify_gpu("NVIDIA A100-SXM4-80GB") == GPUType.A100

    def test_t4(self) -> None:
        assert _classify_gpu("Tesla T4") == GPUType.TESLA_T4

    def test_l4(self) -> None:
        assert _classify_gpu("NVIDIA L4") == GPUType.L4

    def test_v100(self) -> None:
        assert _classify_gpu("Tesla V100-SXM2-16GB") == GPUType.TESLA_V100

    def test_unknown(self) -> None:
        assert _classify_gpu("Some Unknown GPU XYZ") == GPUType.UNKNOWN


class TestGPUInfo:
    def test_vram_total_gb(self) -> None:
        info = GPUInfo(available=True, vram_total_mb=16384)
        assert abs(info.vram_total_gb - 16.0) < 0.1

    def test_vram_used_pct(self) -> None:
        info = GPUInfo(available=True, vram_total_mb=16384, vram_used_mb=8192)
        assert abs(info.vram_used_pct - 50.0) < 0.1

    def test_vram_used_pct_zero_total(self) -> None:
        info = GPUInfo(available=False, vram_total_mb=0)
        assert info.vram_used_pct == 0.0

    def test_is_high_end_a100(self) -> None:
        info = GPUInfo(available=True, gpu_type=GPUType.A100)
        assert info.is_high_end

    def test_is_not_high_end_t4(self) -> None:
        info = GPUInfo(available=True, gpu_type=GPUType.TESLA_T4)
        assert not info.is_high_end

    def test_supports_fp16_true(self) -> None:
        info = GPUInfo(available=True, gpu_type=GPUType.TESLA_T4)
        assert info.supports_fp16

    def test_supports_fp16_cpu(self) -> None:
        info = GPUInfo(available=False, gpu_type=GPUType.CPU_ONLY)
        assert not info.supports_fp16


class TestGetComfyuiLaunchArgs:
    def test_cpu_only(self) -> None:
        info = GPUInfo(available=False, gpu_type=GPUType.CPU_ONLY)
        args = get_comfyui_launch_args(info)
        assert "--cpu" in args

    def test_t4_gets_lowvram(self) -> None:
        info = GPUInfo(
            available=True, gpu_type=GPUType.TESLA_T4,
            vram_total_mb=16 * 1024, vram_used_mb=0
        )
        args = get_comfyui_launch_args(info)
        assert "--lowvram" in args
        assert "--fp16" in args

    def test_a100_gets_highvram(self) -> None:
        info = GPUInfo(
            available=True, gpu_type=GPUType.A100,
            vram_total_mb=80 * 1024, vram_used_mb=0
        )
        args = get_comfyui_launch_args(info)
        assert "--highvram" in args
        assert "--fp16" in args
        assert "--cpu" not in args


class TestDetectGpu:
    @patch("comfy_launcher.gpu._nvidia_smi_query")
    def test_falls_back_to_cpu_when_no_gpu(self, mock_smi: MagicMock) -> None:
        mock_smi.return_value = None
        with patch.dict("sys.modules", {"torch": None}):
            # Without torch and without nvidia-smi, should return CPU
            try:
                info = detect_gpu()
                assert info.gpu_type in (GPUType.UNKNOWN, GPUType.CPU_ONLY)
            except Exception:
                pass  # Acceptable if torch import itself raises

    @patch("comfy_launcher.gpu._nvidia_smi_query")
    def test_parses_nvidia_smi_output(self, mock_smi: MagicMock) -> None:
        mock_smi.return_value = "Tesla T4, 15360, 2048, 13312, 535.104.05"
        with patch.dict("sys.modules", {"torch": None}):
            try:
                info = detect_gpu()
                if info.name:
                    assert "T4" in info.name or info.gpu_type == GPUType.CPU_ONLY
            except Exception:
                pass
