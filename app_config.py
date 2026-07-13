"""Sistema de configuracion jerarquica del estudio.

Carga configuracion desde multiples fuentes en este orden de prioridad
(de menor a mayor, gana la ultima):

  1. config/default.yaml         (commiteado, defaults sensatos)
  2. config/{env}.yaml           (commiteado, segun STUDIO_ENV)
  3. Variables de entorno         (ej: STUDIO_DEBUG=true)
  4. config/user.yaml            (NO commiteado, overrides personales)

Uso:
    from app_config import get_config

    cfg = get_config()
    print(cfg.studio.name)         # "Estudio Inmobiliario AMBA"
    print(cfg.image_generator.backend)  # "auto"
    print(cfg.instagram.default_mode)  # "dry-run"

Variables de entorno reconocidas (todas con prefijo STUDIO_):
    STUDIO_ENV              -- "development" o "production" (default: development)
    STUDIO_DEBUG            -- "true"/"false"
    STUDIO_LOG_LEVEL        -- "DEBUG", "INFO", "WARNING", etc
    STUDIO_FOOOCUS_URL      -- URL de Fooocus
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = REPO_ROOT / "config"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "default.yaml"
USER_CONFIG_PATH = CONFIG_DIR / "user.yaml"


@dataclass
class StudioSection:
    name: str = "Estudio Inmobiliario AMBA"
    version: str = "0.1.0"
    debug: bool = False
    timezone: str = "America/Buenos_Aires"
    locale: str = "es_AR"


@dataclass
class LoggingSection:
    level: str = "INFO"
    format: str = "json"
    file: str | None = None
    rotation: str = "10 MB"
    backup_count: int = 5


@dataclass
class PathsSection:
    inmuebles: str = "inmuebles"
    outputs: str = "inmuebles/outputs"
    logs: str = "logs"
    cache: str = ".cache"


@dataclass
class DataSection:
    prompts_file: str = "prompts_inmobiliarios.json"
    captions_file: str = "captions_instagram.json"


@dataclass
class ImageGeneratorSection:
    backend: str = "auto"
    fooocus_url: str = "http://127.0.0.1:7865"
    fooocus_timeout_seconds: int = 600
    cache_results: bool = True
    retry_attempts: int = 3
    retry_backoff_seconds: int = 5


@dataclass
class CalendarSection:
    posts_per_week: int = 5
    distribute_by_day: bool = True
    rotate_projects: bool = True
    include_date_keys: bool = True


@dataclass
class InstagramSection:
    enabled: bool = False
    default_mode: str = "dry-run"

    def __post_init__(self) -> None:
        if self.default_mode not in ("dry-run", "interactivo", "real"):
            raise ValueError(
                f"instagram.default_mode invalido: {self.default_mode}. "
                "Debe ser 'dry-run', 'interactivo' o 'real'."
            )


@dataclass
class StudioConfig:
    """Config completa del estudio."""

    studio: StudioSection = field(default_factory=StudioSection)
    logging: LoggingSection = field(default_factory=LoggingSection)
    paths: PathsSection = field(default_factory=PathsSection)
    data: DataSection = field(default_factory=DataSection)
    image_generator: ImageGeneratorSection = field(default_factory=ImageGeneratorSection)
    calendar: CalendarSection = field(default_factory=CalendarSection)
    instagram: InstagramSection = field(default_factory=InstagramSection)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Hace merge recursivo. override gana sobre base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    """Carga un YAML y devuelve dict vacio si el archivo no existe."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """Aplica overrides desde variables de entorno STUDIO_*."""
    env_map = {
        "STUDIO_DEBUG": ("studio", "debug", lambda v: v.lower() == "true"),
        "STUDIO_LOG_LEVEL": ("logging", "level", str),
        "STUDIO_FOOOCUS_URL": ("image_generator", "fooocus_url", str),
    }
    for env_var, (section, key, transform) in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            config.setdefault(section, {})[key] = transform(value)
    return config


def _dataclass_from_dict(cls, data: dict[str, Any]) -> Any:
    """Crea una instancia de dataclass desde dict, ignorando keys desconocidas."""
    if not isinstance(data, dict):
        return cls()
    valid_keys = {f.name for f in fields(cls)}
    filtered = {k: v for k, v in data.items() if k in valid_keys}
    return cls(**filtered)


def _build_config(data: dict[str, Any]) -> StudioConfig:
    """Construye StudioConfig desde un dict (merge de todas las fuentes)."""
    return StudioConfig(
        studio=_dataclass_from_dict(StudioSection, data.get("studio", {})),
        logging=_dataclass_from_dict(LoggingSection, data.get("logging", {})),
        paths=_dataclass_from_dict(PathsSection, data.get("paths", {})),
        data=_dataclass_from_dict(DataSection, data.get("data", {})),
        image_generator=_dataclass_from_dict(
            ImageGeneratorSection, data.get("image_generator", {})),
        calendar=_dataclass_from_dict(CalendarSection, data.get("calendar", {})),
        instagram=_dataclass_from_dict(
            InstagramSection, data.get("instagram", {})),
    )


def load_config(env: str | None = None) -> StudioConfig:
    """Carga la configuracion con prioridad (menor a mayor):
        default -> env-specific -> env vars -> user
    """
    if env is None:
        env = os.environ.get("STUDIO_ENV", "development")
    if env not in ("development", "production"):
        raise ValueError(f"env invalido: {env}")

    merged: dict[str, Any] = {}
    merged = _deep_merge(merged, _load_yaml(DEFAULT_CONFIG_PATH))

    env_config_path = CONFIG_DIR / f"{env}.yaml"
    if env_config_path.exists():
        merged = _deep_merge(merged, _load_yaml(env_config_path))

    merged = _apply_env_overrides(merged)

    if USER_CONFIG_PATH.exists():
        merged = _deep_merge(merged, _load_yaml(USER_CONFIG_PATH))

    return _build_config(merged)


_cached_config: StudioConfig | None = None


def get_config() -> StudioConfig:
    """Devuelve la configuracion cacheada. Carga una sola vez."""
    global _cached_config
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config


def reload_config() -> StudioConfig:
    """Fuerza recarga de configuracion (util para tests)."""
    global _cached_config
    _cached_config = None
    return get_config()


if __name__ == "__main__":
    config = get_config()
    print("=== Configuracion cargada ===")
    print(f"Estudio: {config.studio.name} v{config.studio.version}")
    print(f"Debug: {config.studio.debug}")
    print(f"Log level: {config.logging.level} ({config.logging.format})")
    print(f"Image generator: {config.image_generator.backend}")
    print(f"Fooocus URL: {config.image_generator.fooocus_url}")
    print(f"Posts/semana: {config.calendar.posts_per_week}")
    print(f"Instagram enabled: {config.instagram.enabled}")
    print(f"Instagram mode: {config.instagram.default_mode}")
