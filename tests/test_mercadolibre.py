"""Tests del modulo mercadolibre_publisher.py.

Cubre:
  - PublicacionML: to_dict, round_trip
  - ResultadoPublicacionML: resumen
  - MercadoLibrePublisher: configurado, dry-run, mock real, listar, eliminar, buscar
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mercadolibre_publisher import (
    CATEGORIAS,
    MercadoLibrePublisher,
    ModoPublicacion,
    PublicacionML,
    ResultadoPublicacionML,
)


def _write_auth(data: dict, path: Path) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class TestPublicacionML:
    def test_to_dict_minimal(self):
        pub = PublicacionML(titulo="Chacra 5ha", precio=150000)
        d = pub.to_dict()
        assert d["title"] == "Chacra 5ha"
        assert d["price"] == 150000
        assert d["currency_id"] == "USD"
        assert d["category_id"] == CATEGORIAS["terreno"]
        assert d["condition"] == "used"
        assert d["listing_type_id"] == "free"

    def test_to_dict_con_atributos(self):
        pub = PublicacionML(
            titulo="Lote",
            precio=50000,
            atributos={"SUPERFICIE_TOTAL": "500 m2"},
        )
        d = pub.to_dict()
        assert len(d["attributes"]) == 1
        assert d["attributes"][0]["id"] == "SUPERFICIE_TOTAL"

    def test_to_dict_con_ubicacion(self):
        pub = PublicacionML(
            titulo="Campo",
            precio=200000,
            ubicacion={"state": "Buenos Aires", "city": "Cañuelas"},
        )
        d = pub.to_dict()
        assert d["location"]["state"] == "Buenos Aires"


class TestResultadoPublicacionML:
    def test_resumen_dry_run(self):
        r = ResultadoPublicacionML(
            ok=True,
            mode="dry-run",
            dry_run_data={"title": "Chacra"},
        )
        assert "DRY-RUN" in r.resumen()
        assert "Chacra" in r.resumen()

    def test_resumen_real_ok(self):
        r = ResultadoPublicacionML(
            ok=True,
            mode="real",
            permalink="https://articulo.mercadolibre.com.ar/MLA-123",
        )
        assert "MLA-123" in r.resumen()

    def test_resumen_error(self):
        r = ResultadoPublicacionML(ok=False, mode="real", error="Timeout")
        assert "Timeout" in r.resumen()


class TestMercadoLibrePublisher:
    def test_no_configurado_sin_auth(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no_existe.json")
        assert pub.configurado() is False

    def test_configurado_con_auth(self, tmp_path):
        _write_auth(
            {
                "mercadolibre": {
                    "client_id": "x",
                    "client_secret": "y",
                    "access_token": "token_abc",
                }
            },
            tmp_path / "auth.json",
        )
        pub = MercadoLibrePublisher(auth_path=tmp_path / "auth.json")
        assert pub.configurado() is True

    def test_dry_run_no_necesita_auth(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no_existe.json")
        result = pub.crear_publicacion(
            titulo="Chacra 5ha",
            precio=150000,
            modo=ModoPublicacion.DRY_RUN,
        )
        assert result.ok is True
        assert result.mode == "dry-run"
        assert result.dry_run_data is not None
        assert result.dry_run_data["title"] == "Chacra 5ha"

    def test_real_falla_sin_auth(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no_existe.json")
        result = pub.crear_publicacion(
            titulo="Chacra 5ha",
            precio=150000,
            modo=ModoPublicacion.REAL,
        )
        assert result.ok is False
        assert "configurado" in result.error.lower()

    def test_listar_falla_sin_auth(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no_existe.json")
        assert pub.listar_publicaciones() == []

    def test_eliminar_falla_sin_auth(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no_existe.json")
        assert pub.eliminar_publicacion("MLA-123") is False

    def test_mock_real_con_api(self, tmp_path):
        _write_auth(
            {
                "mercadolibre": {
                    "client_id": "x",
                    "client_secret": "y",
                    "access_token": "token_abc",
                }
            },
            tmp_path / "auth.json",
        )
        pub = MercadoLibrePublisher(auth_path=tmp_path / "auth.json")

        mock_response = {
            "id": "MLA-123456",
            "permalink": "https://articulo.mercadolibre.com.ar/MLA-123456",
        }

        with patch(
            "mercadolibre_publisher.MercadoLibrePublisher._request", return_value=mock_response
        ) as mock_req:
            result = pub.crear_publicacion(
                titulo="Chacra 5ha",
                precio=150000,
                modo=ModoPublicacion.REAL,
            )
            assert result.ok is True
            assert result.item_id == "MLA-123456"
            mock_req.assert_called()

    def test_buscar_publicaciones(self, tmp_path):
        _write_auth(
            {
                "mercadolibre": {
                    "access_token": "token_abc",
                }
            },
            tmp_path / "auth.json",
        )
        pub = MercadoLibrePublisher(auth_path=tmp_path / "auth.json")

        mock_response = {"results": [{"id": "MLA-1", "title": "Chacra"}]}
        with patch.object(pub, "_request", return_value=mock_response):
            results = pub.buscar_publicaciones("chacra cañuelas")
            assert len(results) == 1

    def test_categorias_covered(self):
        assert "terreno" in CATEGORIAS
        assert "casa" in CATEGORIAS
        assert "chacra" in CATEGORIAS
        assert "lote" in CATEGORIAS
        assert "campo" in CATEGORIAS
