"""Tests del modulo zonaprop_publisher.py.

Cubre:
  - PublicacionZonaprop: to_dict
  - ResultadoPublicacionZP: resumen
  - ZonapropPublisher: configurado, dry-run, mock real, listar, eliminar, buscar
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zonaprop_publisher import (
    TIPOS_PROPIEDAD,
    ModoPublicacion,
    PublicacionZonaprop,
    ResultadoPublicacionZP,
    ZonapropPublisher,
)


def _write_auth(data: dict, path: Path) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class TestPublicacionZonaprop:
    def test_to_dict_minimal(self):
        pub = PublicacionZonaprop(titulo="Chacra 5ha", precio=150000)
        d = pub.to_dict()
        assert d["title"] == "Chacra 5ha"
        assert d["price"] == 150000
        assert d["currency"] == "USD"
        assert d["property_type"] == "Terreno"
        assert d["operation"] == "venta"

    def test_to_dict_con_superficie(self):
        pub = PublicacionZonaprop(
            titulo="Lote",
            precio=50000,
            superficie=500.0,
            tipo_propiedad="lote",
        )
        d = pub.to_dict()
        assert d["surface"] == 500.0
        assert d["property_type"] == "Lote"


class TestResultadoPublicacionZP:
    def test_resumen_dry_run(self):
        r = ResultadoPublicacionZP(
            ok=True,
            mode="dry-run",
            dry_run_data={"title": "Chacra"},
        )
        assert "DRY-RUN" in r.resumen()
        assert "Zonaprop" in r.resumen()

    def test_resumen_real_ok(self):
        r = ResultadoPublicacionZP(
            ok=True,
            mode="real",
            permalink="https://www.zonaprop.com.ar/propiedades/123",
        )
        assert "123" in r.resumen()

    def test_resumen_error(self):
        r = ResultadoPublicacionZP(ok=False, mode="real", error="Timeout")
        assert "Timeout" in r.resumen()


class TestZonapropPublisher:
    def test_no_configurado_sin_auth(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no_existe.json")
        assert pub.configurado() is False

    def test_configurado_con_auth(self, tmp_path):
        _write_auth(
            {
                "zonaprop": {
                    "email": "test@test.com",
                    "password": "pass123",
                }
            },
            tmp_path / "auth.json",
        )
        pub = ZonapropPublisher(auth_path=tmp_path / "auth.json")
        assert pub.configurado() is True

    def test_dry_run_no_necesita_auth(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no_existe.json")
        result = pub.crear_publicacion(
            titulo="Chacra 5ha",
            precio=150000,
            modo=ModoPublicacion.DRY_RUN,
        )
        assert result.ok is True
        assert result.mode == "dry-run"
        assert result.dry_run_data is not None

    def test_real_falla_sin_auth(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no_existe.json")
        result = pub.crear_publicacion(
            titulo="Chacra 5ha",
            precio=150000,
            modo=ModoPublicacion.REAL,
        )
        assert result.ok is False
        assert "configurado" in result.error.lower()

    def test_listar_falla_sin_auth(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no_existe.json")
        assert pub.listar_publicaciones() == []

    def test_eliminar_falla_sin_auth(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no_existe.json")
        assert pub.eliminar_publicacion("123") is False

    def test_mock_real_con_api(self, tmp_path):
        _write_auth(
            {
                "zonaprop": {
                    "email": "test@test.com",
                    "password": "pass123",
                }
            },
            tmp_path / "auth.json",
        )
        pub = ZonapropPublisher(auth_path=tmp_path / "auth.json")

        mock_response = {
            "id": "ZP-789",
            "permalink": "https://www.zonaprop.com.ar/propiedades/ZP-789",
        }

        with patch.object(pub, "login", return_value=True):
            with patch("zonaprop_publisher.ZonapropPublisher._request", return_value=mock_response):
                result = pub.crear_publicacion(
                    titulo="Chacra 5ha",
                    precio=150000,
                    modo=ModoPublicacion.REAL,
                )
                assert result.ok is True
                assert result.publicacion_id == "ZP-789"

    def test_tipos_propiedad_covered(self):
        assert "terreno" in TIPOS_PROPIEDAD
        assert "casa" in TIPOS_PROPIEDAD
        assert "chacra" in TIPOS_PROPIEDAD
        assert "lote" in TIPOS_PROPIEDAD
        assert "campo" in TIPOS_PROPIEDAD
