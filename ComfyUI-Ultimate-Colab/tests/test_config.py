"""
tests/test_config.py — Unit tests for the Config class.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from comfy_launcher.config import Config, get_config, reset_config


class TestConfigLoading:
    def test_loads_from_file(self, cfg_file: Path, config_data: dict) -> None:
        cfg = Config(config_path=cfg_file)
        assert cfg.comfyui_port == config_data["comfyui"]["port"]

    def test_returns_default_when_key_missing(self, cfg_file: Path) -> None:
        cfg = Config(config_path=cfg_file)
        assert cfg.get("nonexistent.key", "default_value") == "default_value"

    def test_dotted_key_access(self, cfg_file: Path) -> None:
        cfg = Config(config_path=cfg_file)
        assert cfg.get("tunnel.provider") == "cloudflare"

    def test_nested_key(self, cfg_file: Path) -> None:
        cfg = Config(config_path=cfg_file)
        val = cfg.get("models.model_dirs.loras")
        assert val == "models/loras"

    def test_missing_file_uses_defaults(self, tmp_path: Path) -> None:
        cfg = Config(config_path=tmp_path / "nonexistent.json")
        # Should not raise; returns None for any key
        assert cfg.get("any.key") is None

    def test_invalid_json_uses_defaults(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("this is not json")
        cfg = Config(config_path=bad)
        assert cfg.get("any.key") is None


class TestConfigSet:
    def test_set_and_get(self, cfg_file: Path) -> None:
        cfg = Config(config_path=cfg_file)
        cfg.set("comfyui.port", 9999)
        assert cfg.get("comfyui.port") == 9999

    def test_set_new_key(self, cfg_file: Path) -> None:
        cfg = Config(config_path=cfg_file)
        cfg.set("new_section.key", "hello")
        assert cfg.get("new_section.key") == "hello"

    def test_overrides_on_init(self, cfg_file: Path) -> None:
        cfg = Config(config_path=cfg_file, overrides={"comfyui.port": 1234})
        assert cfg.get("comfyui.port") == 1234


class TestConfigEnvOverrides:
    def test_env_override(self, cfg_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COMFY_COMFYUI__PORT", "7777")
        cfg = Config(config_path=cfg_file)
        assert cfg.get("comfyui.port") == 7777

    def test_env_bool_true(self, cfg_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COMFY_DRIVE__ENABLED", "true")
        cfg = Config(config_path=cfg_file)
        assert cfg.get("drive.enabled") is True

    def test_env_bool_false(self, cfg_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COMFY_DRIVE__ENABLED", "false")
        cfg = Config(config_path=cfg_file)
        assert cfg.get("drive.enabled") is False


class TestConfigProperties:
    def test_comfyui_dir(self, cfg: Config, tmp_path: Path) -> None:
        assert cfg.comfyui_dir == tmp_path / "ComfyUI"

    def test_comfyui_port(self, cfg: Config) -> None:
        assert cfg.comfyui_port == 8188

    def test_tunnel_provider(self, cfg: Config) -> None:
        assert cfg.tunnel_provider == "cloudflare"

    def test_civitai_api_key_env(
        self, cfg_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CIVITAI_API_KEY", "test_key")
        cfg = Config(config_path=cfg_file)
        assert cfg.civitai_api_key == "test_key"


class TestConfigSave:
    def test_save_and_reload(self, cfg_file: Path, tmp_path: Path) -> None:
        cfg = Config(config_path=cfg_file)
        cfg.set("comfyui.port", 5555)
        out_path = tmp_path / "saved.json"
        cfg.save(out_path)
        cfg2 = Config(config_path=out_path)
        assert cfg2.get("comfyui.port") == 5555


class TestSingleton:
    def test_get_config_returns_same_instance(self, cfg_file: Path) -> None:
        c1 = get_config(config_path=cfg_file)
        c2 = get_config()
        assert c1 is c2

    def test_reset_config_clears_singleton(self, cfg_file: Path) -> None:
        c1 = get_config(config_path=cfg_file)
        reset_config()
        c2 = get_config(config_path=cfg_file)
        assert c1 is not c2
