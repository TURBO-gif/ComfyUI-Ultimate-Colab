"""
tests/test_utils.py — Unit tests for comfy_launcher.utils.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from comfy_launcher.utils import (
    chunk_list,
    filename_from_url,
    human_duration,
    human_size,
    is_model_file,
    is_url,
    slugify,
    truncate,
)


class TestHumanSize:
    def test_bytes(self) -> None:
        assert human_size(500) == "500.0 B"

    def test_kilobytes(self) -> None:
        assert "KB" in human_size(2048)

    def test_megabytes(self) -> None:
        assert "MB" in human_size(5 * 1024 * 1024)

    def test_gigabytes(self) -> None:
        assert "GB" in human_size(2 * 1024 ** 3)


class TestHumanDuration:
    def test_seconds(self) -> None:
        assert human_duration(45) == "45s"

    def test_minutes(self) -> None:
        assert human_duration(90) == "1m 30s"

    def test_hours(self) -> None:
        assert human_duration(3661) == "1h 1m 1s"


class TestSlugify:
    def test_basic(self) -> None:
        assert slugify("Hello World") == "hello_world"

    def test_special_chars(self) -> None:
        assert slugify("My Model (v1.2)!") == "my_model_v12"

    def test_already_slug(self) -> None:
        assert slugify("my_model") == "my_model"


class TestTruncate:
    def test_no_truncation(self) -> None:
        assert truncate("short", 80) == "short"

    def test_truncates(self) -> None:
        result = truncate("a" * 100, 50)
        assert len(result) == 50
        assert result.endswith("…")


class TestIsUrl:
    def test_http_url(self) -> None:
        assert is_url("http://example.com/file.bin")

    def test_https_url(self) -> None:
        assert is_url("https://huggingface.co/model/resolve/main/f.safetensors")

    def test_not_url(self) -> None:
        assert not is_url("/local/path/to/file.txt")

    def test_ftp_not_url(self) -> None:
        assert not is_url("ftp://example.com/file")


class TestFilenameFromUrl:
    def test_simple(self) -> None:
        assert filename_from_url("https://example.com/model.safetensors") == "model.safetensors"

    def test_with_query(self) -> None:
        name = filename_from_url("https://example.com/file.bin?token=abc")
        assert name == "file.bin"

    def test_no_filename(self) -> None:
        name = filename_from_url("https://example.com/")
        assert name == "download"


class TestIsModelFile:
    def test_safetensors(self) -> None:
        assert is_model_file(Path("model.safetensors"))

    def test_ckpt(self) -> None:
        assert is_model_file(Path("model.ckpt"))

    def test_pt(self) -> None:
        assert is_model_file(Path("model.pt"))

    def test_json_is_not_model(self) -> None:
        assert not is_model_file(Path("config.json"))

    def test_txt_is_not_model(self) -> None:
        assert not is_model_file(Path("requirements.txt"))


class TestChunkList:
    def test_even_split(self) -> None:
        result = chunk_list([1, 2, 3, 4], 2)
        assert result == [[1, 2], [3, 4]]

    def test_uneven_split(self) -> None:
        result = chunk_list([1, 2, 3], 2)
        assert result == [[1, 2], [3]]

    def test_empty(self) -> None:
        assert chunk_list([], 5) == []
