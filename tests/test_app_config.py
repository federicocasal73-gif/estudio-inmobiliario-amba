"""Tests de la clase StudioConfig y carga jerarquica.

Patron: AAA (Arrange-Act-Assert) siguiendo python-testing-patterns skill.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app_config import (
    InstagramSection,
    StudioConfig,
    _apply_env_overrides,
    _deep_merge,
    _load_yaml,
    load_config,
)


class TestDeepMerge:
    """Tests del helper de merge recursivo."""

    def test_merge_with_simple_keys(self):
        # Arrange
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        # Act
        result = _deep_merge(base, override)

        # Assert
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_with_nested_dicts(self):
        # Arrange
        base = {"x": {"a": 1, "b": 2}, "y": 5}
        override = {"x": {"b": 20, "c": 30}}

        # Act
        result = _deep_merge(base, override)

        # Assert
        assert result == {"x": {"a": 1, "b": 20, "c": 30}, "y": 5}

    def test_merge_does_not_mutate_inputs(self):
        # Arrange
        base = {"a": 1}
        override = {"b": 2}

        # Act
        result = _deep_merge(base, override)
        original_base = {"a": 1}
        original_override = {"b": 2}

        # Assert
        assert base == original_base
        assert override == original_override
        assert result is not base
        assert result is not override


class TestLoadYaml:
    """Tests de carga de archivos YAML."""

    def test_load_existing_file(self, tmp_path: Path):
        # Arrange
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("a: 1\nb: hello\n")

        # Act
        result = _load_yaml(yaml_file)

        # Assert
        assert result == {"a": 1, "b": "hello"}

    def test_load_missing_file_returns_empty(self, tmp_path: Path):
        # Arrange
        nonexistent = tmp_path / "does_not_exist.yaml"

        # Act
        result = _load_yaml(nonexistent)

        # Assert
        assert result == {}

    def test_load_empty_file_returns_empty(self, tmp_path: Path):
        # Arrange
        empty = tmp_path / "empty.yaml"
        empty.write_text("")

        # Act
        result = _load_yaml(empty)

        # Assert
        assert result == {}


class TestEnvOverrides:
    """Tests de overrides por variables de entorno."""

    def test_studio_debug_true(self):
        # Arrange
        config = {}

        # Act
        result = _apply_env_overrides(
            _set_env({"STUDIO_DEBUG": "true"}, config))

        # Assert
        assert result["studio"]["debug"] is True

    def test_studio_debug_false(self):
        config = {}
        result = _apply_env_overrides(
            _set_env({"STUDIO_DEBUG": "false"}, config))
        assert result["studio"]["debug"] is False

    def test_studio_log_level(self):
        config = {}
        result = _apply_env_overrides(
            _set_env({"STUDIO_LOG_LEVEL": "WARNING"}, config))
        assert result["logging"]["level"] == "WARNING"

    def test_studio_fooocus_url(self):
        config = {}
        result = _apply_env_overrides(
            _set_env({"STUDIO_FOOOCUS_URL": "http://10.0.0.1:7865"}, config))
        assert result["image_generator"]["fooocus_url"] == "http://10.0.0.1:7865"


def _set_env(env_vars: dict[str, str], config: dict) -> dict:
    """Helper: setea env vars, llama funcion, restaura."""
    saved = {k: os.environ.get(k) for k in env_vars}
    for k, v in env_vars.items():
        os.environ[k] = v
    try:
        result = _apply_env_overrides(config)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return result


class TestLoadConfig:
    """Tests de carga completa de configuracion."""

    def test_load_default_config(self):
        # Arrange (limpiar env)
        os.environ.pop("STUDIO_ENV", None)

        # Act
        config = load_config("development")

        # Assert
        assert isinstance(config, StudioConfig)
        assert config.studio.name == "Estudio Inmobiliario AMBA"
        assert config.studio.timezone == "America/Buenos_Aires"
        assert config.image_generator.backend == "stub"  # development override
        assert config.instagram.enabled is False

    def test_load_production_config(self):
        # Act
        config = load_config("production")

        # Assert
        assert config.instagram.enabled is True
        assert config.instagram.default_mode == "real"
        assert config.calendar.posts_per_week == 7
        assert config.logging.level == "WARNING"

    def test_invalid_env_raises_error(self):
        # Act & Assert
        with pytest.raises(ValueError, match="env invalido"):
            load_config("staging")


class TestSections:
    """Tests de constructores de sub-secciones."""

    def test_instagram_section_validates_mode(self):
        # Act & Assert
        with pytest.raises(ValueError, match="default_mode invalido"):
            InstagramSection(default_mode="invalid-mode")

    def test_instagram_section_accepts_valid_modes(self):
        # Act & Assert (no debe lanzar)
        InstagramSection(default_mode="dry-run")
        InstagramSection(default_mode="interactivo")
        InstagramSection(default_mode="real")
