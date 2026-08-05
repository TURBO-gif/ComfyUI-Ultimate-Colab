"""
tests/test_model_manager.py — Unit tests for model type detection and ModelManager.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from comfy_launcher.constants import DownloadSource, ModelType
from comfy_launcher.model_manager import (
    ModelManager,
    ModelRecord,
    detect_model_type,
    detect_source,
)


class TestDetectModelType:
    def test_flux_url(self) -> None:
        mt = detect_model_type("https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors")
        assert mt == ModelType.DIFFUSION_MODELS

    def test_lora_url(self) -> None:
        mt = detect_model_type("https://civitai.com/models/12345/my-lora-v1")
        assert mt == ModelType.LORAS

    def test_lora_filename(self) -> None:
        mt = detect_model_type("https://example.com/download", filename="my_lora.safetensors")
        assert mt == ModelType.LORAS

    def test_vae_url(self) -> None:
        mt = detect_model_type("https://huggingface.co/stabilityai/sd-vae-ft-mse/resolve/main/diffusion_pytorch_model.safetensors")
        assert mt == ModelType.VAE

    def test_controlnet_url(self) -> None:
        mt = detect_model_type("https://huggingface.co/lllyasviel/sd-controlnet-canny/resolve/main/diffusion_pytorch_model.safetensors")
        assert mt == ModelType.CONTROLNET

    def test_clip_vision_url(self) -> None:
        mt = detect_model_type("https://example.com/clip_vision_model.safetensors")
        assert mt == ModelType.CLIP_VISION

    def test_text_encoder_url(self) -> None:
        mt = detect_model_type("https://example.com/t5xxl_fp16.safetensors")
        assert mt == ModelType.TEXT_ENCODERS

    def test_upscale_url(self) -> None:
        mt = detect_model_type("https://example.com/realesrgan_x4.pth")
        assert mt == ModelType.UPSCALE_MODELS

    def test_default_to_checkpoints(self) -> None:
        mt = detect_model_type("https://example.com/unknownmodel.safetensors")
        assert mt == ModelType.CHECKPOINTS


class TestDetectSource:
    def test_huggingface(self) -> None:
        assert detect_source("https://huggingface.co/repo/file") == DownloadSource.HUGGINGFACE

    def test_civitai(self) -> None:
        assert detect_source("https://civitai.com/models/1234") == DownloadSource.CIVITAI

    def test_github(self) -> None:
        assert detect_source("https://github.com/user/repo/releases") == DownloadSource.GITHUB

    def test_direct(self) -> None:
        assert detect_source("https://example.com/model.safetensors") == DownloadSource.DIRECT


class TestModelRecord:
    def test_size_human(self) -> None:
        rec = ModelRecord(
            name="model.safetensors",
            path="/tmp/model.safetensors",
            model_type="checkpoints",
            size_bytes=1024 * 1024 * 1024,
        )
        assert "GB" in rec.size_human


class TestModelManagerScanDisk:
    def test_scan_finds_safetensors(self, cfg: "Config", paths: "PathResolver", tmp_path: Path) -> None:  # type: ignore[name-defined]
        # Create a fake checkpoint file
        ckpt_dir = paths.models_dir("checkpoints")
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        fake_model = ckpt_dir / "test_model.safetensors"
        fake_model.write_bytes(b"\x00" * 1024)

        mgr = ModelManager(cfg, paths)
        records = mgr.scan_disk()

        names = [r.name for r in records]
        assert "test_model.safetensors" in names

    def test_scan_ignores_non_models(self, cfg: "Config", paths: "PathResolver") -> None:
        ckpt_dir = paths.models_dir("checkpoints")
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        txt_file = ckpt_dir / "readme.txt"
        txt_file.write_text("not a model")

        mgr = ModelManager(cfg, paths)
        records = mgr.scan_disk()
        names = [r.name for r in records]
        assert "readme.txt" not in names
