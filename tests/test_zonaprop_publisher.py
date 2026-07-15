"""Tests del modulo zonaprop_publisher.py.

Cubre:
  - PublicacionZonaprop: to_dict, defaults
  - ResultadoPublicacionZP: resumen (dry-run, ok, error)
  - ZonapropPublisher: _cargar_config, configurado, _request, login,
    crear_publicacion, _upload_image, listar_publicaciones,
    eliminar_publicacion, buscar_propiedades
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from zonaprop_publisher import (
    TIPOS_PROPIEDAD,
    ModoPublicacion,
    PublicacionZonaprop,
    ResultadoPublicacionZP,
    ZonapropPublisher,
)


# ===== PublicacionZonaprop =====


class TestPublicacionZonaprop:
    def test_defaults(self):
        pub = PublicacionZonaprop(titulo="Test", precio=100000)
        assert pub.moneda == "USD"
        assert pub.descripcion == ""
        assert pub.tipo_propiedad == "terreno"
        assert pub.operacion == "venta"
        assert pub.superficie is None
        assert pub.ubicacion == ""
        assert pub.direccion == ""
        assert pub.imagenes == []
        assert pub.atributos == {}
        assert pub.id is None
        assert pub.permalink is None
        assert pub.status == "draft"

    def test_to_dict_minimal(self):
        pub = PublicacionZonaprop(titulo="Chacra 5ha", precio=150000)
        d = pub.to_dict()
        assert d["title"] == "Chacra 5ha"
        assert d["price"] == 150000
        assert d["currency"] == "USD"
        assert d["property_type"] == "Terreno"
        assert d["operation"] == "venta"
        assert d["surface"] is None
        assert d["location"] == ""
        assert d["address"] == ""

    def test_to_dict_completo(self):
        pub = PublicacionZonaprop(
            titulo="Lote en Pilar",
            precio=80000,
            moneda="USD",
            descripcion="Lote ideal",
            tipo_propiedad="lote",
            operacion="alquiler",
            superficie=500,
            ubicacion="Pilar, Buenos Aires",
            direccion="Av. Siempre Viva 123",
            atributos={"covered_surface": "200"},
        )
        d = pub.to_dict()
        assert d["property_type"] == "Lote"
        assert d["operation"] == "alquiler"
        assert d["surface"] == 500
        assert d["location"] == "Pilar, Buenos Aires"
        assert d["attributes"]["covered_surface"] == "200"

    def test_to_dict_tipo_desconocido(self):
        pub = PublicacionZonaprop(titulo="Otro", precio=50000, tipo_propiedad="galpon")
        d = pub.to_dict()
        assert d["property_type"] == "Terreno"  # default


# ===== ResultadoPublicacionZP =====


class TestResultadoPublicacionZP:
    def test_resumen_dry_run(self):
        r = ResultadoPublicacionZP(
            ok=True, mode="dry-run", dry_run_data={"title": "Chacra 5ha"}
        )
        assert "[DRY-RUN]" in r.resumen()
        assert "Zonaprop" in r.resumen()
        assert "Chacra 5ha" in r.resumen()

    def test_resumen_ok(self):
        r = ResultadoPublicacionZP(
            ok=True, mode="real", permalink="https://www.zonaprop.com.ar/propiedad/123"
        )
        assert "Publicado en Zonaprop OK" in r.resumen()
        assert "zonaprop" in r.resumen()

    def test_resumen_error(self):
        r = ResultadoPublicacionZP(ok=False, mode="real", error="Login failed")
        assert "Error Zonaprop" in r.resumen()
        assert "Login failed" in r.resumen()


# ===== ZonapropPublisher._cargar_config =====


class TestCargarConfig:
    def test_config_ok(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {
                "email": "test@email.com",
                "password": "pass123",
                "empresa": "Inmobiliaria",
                "telefono": "+54 11 1234-5678",
            }
        }))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.configurado() is True

    def test_config_no_zonaprop(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({"zonaprop": {}}))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.configurado() is False

    def test_config_no_file(self, tmp_path):
        auth = tmp_path / "nonexistent.json"
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.configurado() is False

    def test_config_bad_json(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text("not json {{{")
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.configurado() is False

    def test_config_no_email(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"password": "pass"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.configurado() is False


# ===== _request =====


class TestRequest:
    def _make_publisher(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {
                "email": "test@email.com",
                "password": "pass123",
            }
        }))
        return ZonapropPublisher(auth_path=auth)

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_request_ok(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": "ZP123"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._request("GET", "/test")
        assert result["id"] == "ZP123"

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_request_full_url(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._request("GET", "https://example.com/api/test")
        assert result["ok"] is True

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_request_with_data(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._request("POST", "/test", data={"key": "val"})
        assert result["ok"] is True

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_request_with_session_cookie(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        pub._session_cookie = "session=abc123"
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._request("GET", "/test")
        assert result["ok"] is True

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_request_with_extra_headers(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._request("GET", "/test", headers={"X-Custom": "value"})
        assert result["ok"] is True

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_request_http_error_json(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        error_resp = MagicMock()
        error_resp.read.return_value = json.dumps({"message": "Not found"}).encode()
        http_error = urllib.error.HTTPError(
            url="/test", code=404, msg="Not Found", hdrs=None, fp=error_resp
        )
        mock_urlopen.side_effect = http_error
        with pytest.raises(RuntimeError, match="Zonaprop API error 404"):
            pub._request("GET", "/test")

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_request_http_error_plain_text(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        error_resp = MagicMock()
        error_resp.read.return_value = b"plain text error"
        http_error = urllib.error.HTTPError(
            url="/test", code=500, msg="Server Error", hdrs=None, fp=error_resp
        )
        mock_urlopen.side_effect = http_error
        with pytest.raises(RuntimeError, match="Zonaprop API error 500"):
            pub._request("GET", "/test")


# ===== login =====


class TestLogin:
    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_login_ok(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"session_cookie": "session=abc"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert pub.login() is True
        assert pub._session_cookie == "session=abc"

    def test_login_no_configurado(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({}))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.login() is False

    @patch("zonaprop_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_login_api_error(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.login() is False


# ===== crear_publicacion =====


class TestCrearPublicacion:
    def _make_publisher(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        return ZonapropPublisher(auth_path=auth)

    def test_dry_run(self, tmp_path):
        pub = self._make_publisher(tmp_path)
        r = pub.crear_publicacion(
            titulo="Chacra 5ha",
            precio=150000,
            modo=ModoPublicacion.DRY_RUN,
        )
        assert r.ok is True
        assert r.mode == "dry-run"
        assert r.dry_run_data["title"] == "Chacra 5ha"

    def test_no_configurado(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({}))
        pub = ZonapropPublisher(auth_path=auth)
        r = pub.crear_publicacion(
            titulo="Test",
            precio=100000,
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is False
        assert "no configurado" in r.error.lower()

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_real_ok(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        # First call: login, second call: create
        login_resp = MagicMock()
        login_resp.read.return_value = json.dumps({"session_cookie": "session=abc"}).encode()
        login_resp.__enter__ = MagicMock(return_value=login_resp)
        login_resp.__exit__ = MagicMock(return_value=False)
        create_resp = MagicMock()
        create_resp.read.return_value = json.dumps({
            "id": "ZP999",
            "permalink": "https://www.zonaprop.com.ar/propiedad/999",
        }).encode()
        create_resp.__enter__ = MagicMock(return_value=create_resp)
        create_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [login_resp, create_resp]
        r = pub.crear_publicacion(
            titulo="Lote",
            precio=80000,
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is True
        assert r.publicacion_id == "ZP999"

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_real_con_imagenes(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff" * 10)
        login_resp = MagicMock()
        login_resp.read.return_value = json.dumps({"session_cookie": "s"}).encode()
        login_resp.__enter__ = MagicMock(return_value=login_resp)
        login_resp.__exit__ = MagicMock(return_value=False)
        create_resp = MagicMock()
        create_resp.read.return_value = json.dumps({"id": "ZP888", "permalink": "https://zp/888"}).encode()
        create_resp.__enter__ = MagicMock(return_value=create_resp)
        create_resp.__exit__ = MagicMock(return_value=False)
        upload_resp = MagicMock()
        upload_resp.read.return_value = json.dumps({"ok": True}).encode()
        upload_resp.__enter__ = MagicMock(return_value=upload_resp)
        upload_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [login_resp, create_resp, upload_resp]
        r = pub.crear_publicacion(
            titulo="Con fotos",
            precio=100000,
            imagenes=[img],
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is True

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_real_login_falla(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_urlopen.side_effect = RuntimeError("Login failed")
        r = pub.crear_publicacion(
            titulo="Test",
            precio=100000,
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is False
        assert "login" in r.error.lower()

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_real_api_error(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        login_resp = MagicMock()
        login_resp.read.return_value = json.dumps({"session_cookie": "s"}).encode()
        login_resp.__enter__ = MagicMock(return_value=login_resp)
        login_resp.__exit__ = MagicMock(return_value=False)
        error_resp = MagicMock()
        error_resp.read.return_value = json.dumps({"message": "Invalid"}).encode()
        http_error = urllib.error.HTTPError(
            url="/test", code=400, msg="Bad Request", hdrs=None, fp=error_resp
        )
        mock_urlopen.side_effect = [login_resp, http_error]
        r = pub.crear_publicacion(
            titulo="Bad",
            precio=50000,
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is False
        assert "400" in r.error

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_real_ya_logueado(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        pub._session_cookie = "existing_session"
        create_resp = MagicMock()
        create_resp.read.return_value = json.dumps({"id": "ZP777", "permalink": "https://zp/777"}).encode()
        create_resp.__enter__ = MagicMock(return_value=create_resp)
        create_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = create_resp
        r = pub.crear_publicacion(
            titulo="Sin login",
            precio=100000,
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is True
        # Only one call (no login call)
        assert mock_urlopen.call_count == 1


# ===== _upload_image =====


class TestUploadImage:
    def _make_publisher(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        return ZonapropPublisher(auth_path=auth)

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_upload_ok(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff" * 10)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": "pic123"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert pub._upload_image("ZP123", img) is True

    @patch("zonaprop_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_upload_error(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff" * 10)
        assert pub._upload_image("ZP123", img) is False


# ===== listar_publicaciones =====


class TestListarPublicaciones:
    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_listar_ok(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        login_resp = MagicMock()
        login_resp.read.return_value = json.dumps({"session_cookie": "s"}).encode()
        login_resp.__enter__ = MagicMock(return_value=login_resp)
        login_resp.__exit__ = MagicMock(return_value=False)
        list_resp = MagicMock()
        list_resp.read.return_value = json.dumps({"results": [{"id": "ZP1"}]}).encode()
        list_resp.__enter__ = MagicMock(return_value=list_resp)
        list_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [login_resp, list_resp]
        result = pub.listar_publicaciones()
        assert len(result) == 1
        assert result[0]["id"] == "ZP1"

    def test_listar_no_configurado(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({}))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.listar_publicaciones() == []

    @patch("zonaprop_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_listar_error(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.listar_publicaciones() == []


# ===== eliminar_publicacion =====


class TestEliminarPublicacion:
    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_eliminar_ok(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert pub.eliminar_publicacion("ZP123") is True

    def test_eliminar_no_configurado(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({}))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.eliminar_publicacion("ZP123") is False

    @patch("zonaprop_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_eliminar_error(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.eliminar_publicacion("ZP123") is False


# ===== buscar_propiedades =====


class TestBuscarPropiedades:
    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_buscar_ok(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"results": [{"id": "ZP1"}]}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.buscar_propiedades("chacra cañuelas")
        assert len(result) == 1

    @patch("zonaprop_publisher.urllib.request.urlopen")
    def test_buscar_con_filtros(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"results": []}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.buscar_propiedades(
            "lote", ubicacion="Pilar", precio_min=50000, precio_max=200000, tipo="lote"
        )
        assert isinstance(result, list)

    @patch("zonaprop_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_buscar_error(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({
            "zonaprop": {"email": "test@email.com", "password": "pass123"}
        }))
        pub = ZonapropPublisher(auth_path=auth)
        assert pub.buscar_propiedades("test") == []


# ===== Constants =====


class TestTiposPropiedad:
    def test_all_keys(self):
        assert "terreno" in TIPOS_PROPIEDAD
        assert "casa" in TIPOS_PROPIEDAD
        assert "lote" in TIPOS_PROPIEDAD
        assert "chacra" in TIPOS_PROPIEDAD
        assert "campo" in TIPOS_PROPIEDAD
        assert "departamento" in TIPOS_PROPIEDAD
        assert "oficina" in TIPOS_PROPIEDAD

    def test_terreno_value(self):
        assert TIPOS_PROPIEDAD["terreno"] == "Terreno"
