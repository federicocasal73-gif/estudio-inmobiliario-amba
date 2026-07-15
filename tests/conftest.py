"""Fixtures compartidos para todos los tests del estudio."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo_root() -> Path:
    """Path a la raiz del repositorio."""
    return REPO_ROOT


@pytest.fixture
def municipios_amba() -> list[str]:
    """Lista de municipios AMBA soportados."""
    return [
        "Pilar",
        "Escobar",
        "Campana",
        "Zarate",
        "Lujan",
        "Mercedes",
        "Canuelas",
        "Lobos",
        "Brandsen",
        "Roque Perez",
        "Chascomus",
        "Tandil",
    ]


@pytest.fixture
def prompts_db() -> dict[str, Any]:
    """Carga el JSON de prompts de prueba."""
    path = REPO_ROOT / "prompts_inmobiliarios.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


@pytest.fixture
def captions_db() -> dict[str, Any]:
    """Carga el JSON de captions de prueba."""
    path = REPO_ROOT / "captions_instagram.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


@pytest.fixture
def sample_post() -> dict[str, Any]:
    """Un post de ejemplo para tests."""
    return {
        "caption": "Hermosa chacra 🌾",
        "caption_completo": "Hermosa chacra 🌾\n\nA 65 km de CABA.\n\n#lotes #chacras",
        "hashtags": ["#lotes", "#chacras"],
        "municipio": "Cañuelas",
        "tipo": "lote_venta",
        "tono": "emotivo",
    }


@pytest.fixture
def mock_fooocus_client():
    """Mock del cliente Fooocus para tests que no requieren red."""
    client = MagicMock()
    client.predict.return_value = ("/tmp/imagen_generada.jpg",)
    return client
