"""Tests para mercadolibre_publisher.py y zonaprop_publisher.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mercadolibre_publisher import (
    MercadoLibrePublisher,
    ModoPublicacion as MLModoPublicacion,
    PublicacionML,
    ResultadoPublicacionML,
    CATEGORIAS,
)
from zonaprop_publisher import (
    ZonapropPublisher,
    ModoPublicacion as ZPModoPublicacion,
    PublicacionZonaprop,
    ResultadoPublicacionZP,
    TIPOS_PROPIEDAD,
)


# ========== MercadoLibre Tests ==========


class TestPublicacionML:
    def test_creation(self):
        p = PublicacionML(titulo="Test", precio=100000)
        assert p.titulo == "Test"
        assert p.precio == 100000
        assert p.moneda == "USD"
        assert p.categoria == "terreno"

    def test_to_dict(self):
        p = PublicacionML(titulo="Test", precio=100000, categoria="casa")
        d = p.to_dict()
        assert d["title"] == "Test"
        assert d["price"] == 100000
        assert d["category_id"] == CATEGORIAS["casa"]

    def test_to_dict_with_location(self):
        p = PublicacionML(
            titulo="T", precio=1, ubicacion={"state": "Buenos Aires", "city": "Canuelas"}
        )
        d = p.to_dict()
        assert "location" in d

    def test_to_dict_with_attributes(self):
        p = PublicacionML(titulo="T", precio=1, atributos={"AREA": "500"})
        d = p.to_dict()
        assert "attributes" in d

    def test_to_dict_no_location(self):
        p = PublicacionML(titulo="T", precio=1)
        d = p.to_dict()
        assert "location" not in d


class TestResultadoPublicacionML:
    def test_dry_run(self):
        r = ResultadoPublicacionML(ok=True, mode="dry-run", dry_run_data={"title": "Test"})
        assert "DRY-RUN" in r.resumen()

    def test_ok(self):
        r = ResultadoPublicacionML(ok=True, mode="real", permalink="https://ml.com/123")
        assert "Publicado OK" in r.resumen()

    def test_error(self):
        r = ResultadoPublicacionML(ok=False, mode="real", error="API error")
        assert "Error" in r.resumen()


class TestMercadoLibrePublisher:
    def _make_auth(self, tmp_path: Path, config: dict | None = None) -> Path:
        auth = tmp_path / "auth.json"
        data = config or {
            "mercadolibre": {
                "client_id": "test_id",
                "client_secret": "test_secret",
                "access_token": "test_token",
                "refresh_token": "test_refresh",
            }
        }
        auth.write_text(json.dumps(data), encoding="utf-8")
        return auth

    def test_init_with_config(self, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.configurado() is True

    def test_init_without_config(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no.json")
        assert pub.configurado() is False

    def test_init_empty_mercadolibre_section(self, tmp_path):
        auth = self._make_auth(tmp_path, config={"mercadolibre": {}})
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.configurado() is False

    def test_dry_run(self, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = MercadoLibrePublisher(auth_path=auth)
        result = pub.crear_publicacion(
            titulo="Chacra 5ha",
            precio=60000,
            modo=MLModoPublicacion.DRY_RUN,
        )
        assert result.ok is True
        assert result.mode == "dry-run"
        assert result.dry_run_data is not None

    def test_real_no_configurado(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no.json")
        result = pub.crear_publicacion(
            titulo="Test",
            precio=100,
            modo=MLModoPublicacion.REAL,
        )
        assert result.ok is False
        assert "configurado" in result.error.lower()

    def test_build_multipart(self, tmp_path):
        f = tmp_path / "img.jpg"
        f.write_bytes(b"\x00" * 100)
        result = MercadoLibrePublisher._build_multipart(
            "boundary", {"key": "value"}, [("file", f)]
        )
        assert b"boundary" in result
        assert b"key" in result
        assert b"value" in result

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_refresh_token(self, mock_urlopen, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "access_token": "new_token",
            "refresh_token": "new_refresh",
        }).encode()
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._refresh_token()
        assert result is True

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_refresh_token_fail(self, mock_urlopen, tmp_path):
        import urllib.error
        auth = self._make_auth(tmp_path, config={
            "mercadolibre": {"client_id": "", "client_secret": "", "refresh_token": ""}
        })
        pub = MercadoLibrePublisher(auth_path=auth)
        result = pub._refresh_token()
        assert result is False

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_listar_publicaciones(self, mock_urlopen, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"results": [{"id": "123"}]}).encode()
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.listar_publicaciones()
        assert len(result) == 1

    def test_listar_no_configurado(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no.json")
        result = pub.listar_publicaciones()
        assert result == []

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_eliminar_publicacion(self, mock_urlopen, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({}).encode()
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.eliminar_publicacion("123")
        assert result is True

    def test_eliminar_no_configurado(self, tmp_path):
        pub = MercadoLibrePublisher(auth_path=tmp_path / "no.json")
        result = pub.eliminar_publicacion("123")
        assert result is False

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_buscar_publicaciones(self, mock_urlopen, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"results": []}).encode()
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.buscar_publicaciones("chacra")
        assert result == []

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_buscar_con_filtros(self, mock_urlopen, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"results": [{"id": "1"}]}).encode()
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.buscar_publicaciones(
            "lote",
            ubicacion="Buenos Aires",
            precio_min=10000,
            precio_max=100000,
        )
        assert isinstance(result, list)


# ========== Zonaprop Tests ==========


class TestPublicacionZonaprop:
    def test_creation(self):
        p = PublicacionZonaprop(titulo="Test", precio=100000)
        assert p.titulo == "Test"
        assert p.precio == 100000
        assert p.tipo_propiedad == "terreno"

    def test_to_dict(self):
        p = PublicacionZonaprop(titulo="Test", precio=100000, tipo_propiedad="casa")
        d = p.to_dict()
        assert d["title"] == "Test"
        assert d["property_type"] == TIPOS_PROPIEDAD["casa"]

    def test_to_dict_with_superficie(self):
        p = PublicacionZonaprop(titulo="T", precio=1, superficie=500)
        d = p.to_dict()
        assert d["surface"] == 500


class TestResultadoPublicacionZP:
    def test_dry_run(self):
        r = ResultadoPublicacionZP(ok=True, mode="dry-run", dry_run_data={"title": "Test"})
        assert "DRY-RUN" in r.resumen()

    def test_ok(self):
        r = ResultadoPublicacionZP(ok=True, mode="real", permalink="https://zp.com/123")
        assert "Publicado en Zonaprop OK" in r.resumen()

    def test_error(self):
        r = ResultadoPublicacionZP(ok=False, mode="real", error="API error")
        assert "Error Zonaprop" in r.resumen()


class TestZonapropPublisher:
    def _make_auth(self, tmp_path: Path, config: dict | None = None) -> Path:
        auth = tmp_path / "auth.json"
        data = config or {
            "zonaprop": {
                "email": "test@email.com",
                "password": "test_pass",
                "empresa": "Test SA",
                "telefono": "+54 11 1234-5678",
            }
        }
        auth.write_text(json.dumps(data), encoding="utf-8")
        return auth

    def test_init_with_config(self, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.configurado() is True

    def test_init_without_config(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no.json")
        assert pub.configurado() is False

    def test_init_empty_zonaprop_section(self, tmp_path):
        auth = self._make_auth(tmp_path, config={"zonaprop": {}})
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.configurado() is False

    def test_dry_run(self, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = ZonapropPublisher(auth_path=auth)
        result = pub.crear_publicacion(
            titulo="Chacra 5ha",
            precio=60000,
            modo=ZPModoPublicacion.DRY_RUN,
        )
        assert result.ok is True
        assert result.mode == "dry-run"

    def test_real_no_configurado(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no.json")
        result = pub.crear_publicacion(
            titulo="Test",
            precio=100,
            modo=ZPModoPublicacion.REAL,
        )
        assert result.ok is False
        assert "configurado" in result.error.lower()

    def test_listar_no_configurado(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no.json")
        result = pub.listar_publicaciones()
        assert result == []

    def test_eliminar_no_configurado(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no.json")
        result = pub.eliminar_publicacion("123")
        assert result is False

    def test_buscar_propiedades(self, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = ZonapropPublisher(auth_path=auth)
        with patch.object(pub, "_request", return_value={"results": []}):
            result = pub.buscar_propiedades("chacra")
            assert result == []

    def test_login_fail_not_configured(self, tmp_path):
        pub = ZonapropPublisher(auth_path=tmp_path / "no.json")
        result = pub.login()
        assert result is False

    def test_request_error(self, tmp_path):
        auth = self._make_auth(tmp_path)
        pub = ZonapropPublisher(auth_path=auth)
        with patch.object(pub, "_request", side_effect=RuntimeError("API error 404")):
            with pytest.raises(RuntimeError):
                pub._request("GET", "/api/test")
