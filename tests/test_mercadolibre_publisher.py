"""Tests del modulo mercadolibre_publisher.py.

Cubre:
  - PublicacionML: to_dict, defaults
  - ResultadoPublicacionML: resumen (dry-run, ok, error)
  - MercadoLibrePublisher: _cargar_config, configurado, _request, _build_multipart,
    _refresh_token, crear_publicacion, _upload_image, listar_publicaciones,
    eliminar_publicacion, buscar_publicaciones
"""

from __future__ import annotations

import json
import urllib.error
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

# ===== PublicacionML =====


class TestPublicacionML:
    def test_defaults(self):
        pub = PublicacionML(titulo="Test", precio=100000)
        assert pub.moneda == "USD"
        assert pub.descripcion == ""
        assert pub.categoria == "terreno"
        assert pub.estado == "used"
        assert pub.ubicacion == {}
        assert pub.imagenes == []
        assert pub.atributos == {}
        assert pub.id is None
        assert pub.permalink is None
        assert pub.status == "draft"

    def test_to_dict_minimal(self):
        pub = PublicacionML(titulo="Chacra 5ha", precio=150000)
        d = pub.to_dict()
        assert d["title"] == "Chacra 5ha"
        assert d["price"] == 150000
        assert d["currency_id"] == "USD"
        assert d["category_id"] == "MLA1459"
        assert d["condition"] == "used"
        assert d["listing_type_id"] == "free"
        assert "location" not in d
        assert "attributes" not in d

    def test_to_dict_con_ubicacion(self):
        pub = PublicacionML(
            titulo="Test",
            precio=50000,
            ubicacion={"state": "Buenos Aires", "city": "Cañuelas"},
        )
        d = pub.to_dict()
        assert "location" in d
        assert d["location"]["city"] == "Cañuelas"

    def test_to_dict_con_atributos(self):
        pub = PublicacionML(
            titulo="Test",
            precio=50000,
            atributos={"surface_total": "5000", "land_type": "chacra"},
        )
        d = pub.to_dict()
        assert "attributes" in d
        assert len(d["attributes"]) == 2
        assert d["attributes"][0]["id"] == "surface_total"

    def test_to_dict_categoria_casa(self):
        pub = PublicacionML(titulo="Casa", precio=200000, categoria="casa")
        d = pub.to_dict()
        assert d["category_id"] == "MLA1472"

    def test_to_dict_categoria_desconocida(self):
        pub = PublicacionML(titulo="Otro", precio=50000, categoria="otra")
        d = pub.to_dict()
        assert d["category_id"] == CATEGORIAS["terreno"]


# ===== ResultadoPublicacionML =====


class TestResultadoPublicacionML:
    def test_resumen_dry_run(self):
        r = ResultadoPublicacionML(ok=True, mode="dry-run", dry_run_data={"title": "Chacra 5ha"})
        assert "[DRY-RUN]" in r.resumen()
        assert "Chacra 5ha" in r.resumen()

    def test_resumen_ok(self):
        r = ResultadoPublicacionML(
            ok=True, mode="real", permalink="https://articulo.mercadolibre.com.ar/MLA-123"
        )
        assert "Publicado OK" in r.resumen()
        assert "mercadolibre" in r.resumen()

    def test_resumen_error(self):
        r = ResultadoPublicacionML(ok=False, mode="real", error="API timeout")
        assert "Error" in r.resumen()
        assert "API timeout" in r.resumen()


# ===== MercadoLibrePublisher._cargar_config =====


class TestCargarConfig:
    def test_config_ok(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "123",
                        "client_secret": "sec",
                        "access_token": "tok123",
                        "refresh_token": "ref123",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.configurado() is True

    def test_config_no_mercadolibre(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({"mercadolibre": {}}))
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.configurado() is False

    def test_config_no_file(self, tmp_path):
        auth = tmp_path / "nonexistent.json"
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.configurado() is False

    def test_config_bad_json(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text("not json {{{")
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.configurado() is False

    def test_config_no_access_token(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "123",
                        "client_secret": "sec",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.configurado() is False


# ===== _build_multipart =====


class TestBuildMultipart:
    def test_with_fields_and_files(self, tmp_path):
        f1 = tmp_path / "photo.jpg"
        f1.write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)
        boundary = "----TestBoundary"
        fields = {"title": "Test", "price": "100000"}
        files = [("file", f1)]
        result = MercadoLibrePublisher._build_multipart(boundary, fields, files)
        assert isinstance(result, bytes)
        assert b"----TestBoundary" in result
        assert b"Test" in result
        assert b"photo.jpg" in result

    def test_fields_only(self):
        boundary = "----TestBoundary"
        fields = {"key": "value"}
        result = MercadoLibrePublisher._build_multipart(boundary, fields, [])
        assert b"key" in result
        assert b"value" in result
        assert b"----TestBoundary--" in result


# ===== _request =====


class TestRequest:
    def _make_publisher(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "123",
                        "client_secret": "sec",
                        "access_token": "tok123",
                        "refresh_token": "ref123",
                    }
                }
            )
        )
        return MercadoLibrePublisher(auth_path=auth)

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_request_ok(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": "MLA123"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._request("GET", "/test")
        assert result["id"] == "MLA123"

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_request_http_error_json(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        error_resp = MagicMock()
        error_resp.read.return_value = json.dumps({"message": "Not found"}).encode()
        http_error = urllib.error.HTTPError(
            url="/test", code=404, msg="Not Found", hdrs=None, fp=error_resp
        )
        mock_urlopen.side_effect = http_error
        with pytest.raises(RuntimeError, match="ML API error 404"):
            pub._request("GET", "/test")

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_request_http_error_plain_text(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        error_resp = MagicMock()
        error_resp.read.return_value = b"plain text error"
        http_error = urllib.error.HTTPError(
            url="/test", code=500, msg="Server Error", hdrs=None, fp=error_resp
        )
        mock_urlopen.side_effect = http_error
        with pytest.raises(RuntimeError, match="ML API error 500"):
            pub._request("GET", "/test")

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_request_with_data(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._request("POST", "/test", data={"key": "val"})
        assert result["ok"] is True

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_request_with_files(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        f = tmp_path / "img.jpg"
        f.write_bytes(b"\xff" * 10)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub._request("POST", "/test", data={"title": "x"}, files=[("file", f)])
        assert result["ok"] is True


# ===== _refresh_token =====


class TestRefreshToken:
    def _make_publisher(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "123",
                        "client_secret": "sec",
                        "access_token": "old_token",
                        "refresh_token": "ref123",
                    }
                }
            )
        )
        return MercadoLibrePublisher(auth_path=auth)

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_refresh_ok(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "access_token": "new_token",
                "refresh_token": "new_refresh",
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert pub._refresh_token() is True
        assert pub._config["access_token"] == "new_token"
        assert pub._config["refresh_token"] == "new_refresh"

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_refresh_ok_sin_nuevo_refresh(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "access_token": "new_token",
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert pub._refresh_token() is True
        assert pub._config["access_token"] == "new_token"
        assert pub._config["refresh_token"] == "ref123"  # unchanged

    @patch(
        "mercadolibre_publisher.urllib.request.urlopen", side_effect=urllib.error.URLError("fail")
    )
    def test_refresh_falla(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        assert pub._refresh_token() is False

    def test_refresh_missing_fields(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({"mercadolibre": {"access_token": "tok"}}))
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub._refresh_token() is False


# ===== crear_publicacion =====


class TestCrearPublicacion:
    def _make_publisher(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "123",
                        "client_secret": "sec",
                        "access_token": "tok123",
                        "refresh_token": "ref123",
                    }
                }
            )
        )
        return MercadoLibrePublisher(auth_path=auth)

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
        pub = MercadoLibrePublisher(auth_path=auth)
        r = pub.crear_publicacion(
            titulo="Test",
            precio=100000,
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is False
        assert "no configurado" in r.error.lower()

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_real_ok(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "id": "MLA999",
                "permalink": "https://articulo.mercadolibre.com.ar/MLA-999",
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        r = pub.crear_publicacion(
            titulo="Lote",
            precio=80000,
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is True
        assert r.item_id == "MLA999"
        assert "mercadolibre" in r.permalink

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_real_con_imagenes(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff" * 10)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "id": "MLA888",
                "permalink": "https://articulo.mercadolibre.com.ar/MLA-888",
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        r = pub.crear_publicacion(
            titulo="Con fotos",
            precio=100000,
            imagenes=[img],
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is True

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_api_error(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        error_resp = MagicMock()
        error_resp.read.return_value = json.dumps({"message": "Invalid params"}).encode()
        http_error = urllib.error.HTTPError(
            url="/test", code=400, msg="Bad Request", hdrs=None, fp=error_resp
        )
        mock_urlopen.side_effect = http_error
        r = pub.crear_publicacion(
            titulo="Bad",
            precio=50000,
            modo=ModoPublicacion.REAL,
        )
        assert r.ok is False
        assert "400" in r.error

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_interactivo_ok(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {
                "id": "MLA777",
                "permalink": "https://articulo.mercadolibre.com.ar/MLA-777",
            }
        ).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        r = pub.crear_publicacion(
            titulo="Interactivo",
            precio=100000,
            modo=ModoPublicacion.INTERACTIVO,
        )
        assert r.ok is True
        # interactivo does NOT auto-activate (only real does)
        assert r.item_id == "MLA777"


# ===== _upload_image =====


class TestUploadImage:
    def _make_publisher(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "123",
                        "client_secret": "sec",
                        "access_token": "tok123",
                        "refresh_token": "ref123",
                    }
                }
            )
        )
        return MercadoLibrePublisher(auth_path=auth)

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_upload_ok(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff" * 10)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": "pic123"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert pub._upload_image("MLA123", img) is True

    @patch("mercadolibre_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_upload_error(self, mock_urlopen, tmp_path):
        pub = self._make_publisher(tmp_path)
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff" * 10)
        assert pub._upload_image("MLA123", img) is False


# ===== listar_publicaciones =====


class TestListarPublicaciones:
    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_listar_ok(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "123",
                        "client_secret": "sec",
                        "access_token": "tok",
                        "refresh_token": "ref",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"results": [{"id": "MLA1"}]}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.listar_publicaciones()
        assert len(result) == 1
        assert result[0]["id"] == "MLA1"

    def test_listar_no_configurado(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({}))
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.listar_publicaciones() == []

    @patch("mercadolibre_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_listar_error(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "1",
                        "client_secret": "s",
                        "access_token": "t",
                        "refresh_token": "r",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.listar_publicaciones() == []


# ===== eliminar_publicacion =====


class TestEliminarPublicacion:
    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_eliminar_ok(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "1",
                        "client_secret": "s",
                        "access_token": "t",
                        "refresh_token": "r",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert pub.eliminar_publicacion("MLA123") is True

    def test_eliminar_no_configurado(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({}))
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.eliminar_publicacion("MLA123") is False

    @patch("mercadolibre_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_eliminar_error(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "1",
                        "client_secret": "s",
                        "access_token": "t",
                        "refresh_token": "r",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.eliminar_publicacion("MLA123") is False


# ===== buscar_publicaciones =====


class TestBuscarPublicaciones:
    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_buscar_ok(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "1",
                        "client_secret": "s",
                        "access_token": "t",
                        "refresh_token": "r",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"results": [{"id": "MLA1"}]}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.buscar_publicaciones("chacra cañuelas")
        assert len(result) == 1

    @patch("mercadolibre_publisher.urllib.request.urlopen")
    def test_buscar_con_filtros(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "1",
                        "client_secret": "s",
                        "access_token": "t",
                        "refresh_token": "r",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"results": []}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = pub.buscar_publicaciones(
            "lote", ubicacion="Buenos Aires", precio_min=50000, precio_max=200000
        )
        assert isinstance(result, list)

    @patch("mercadolibre_publisher.urllib.request.urlopen", side_effect=RuntimeError("fail"))
    def test_buscar_error(self, mock_urlopen, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(
            json.dumps(
                {
                    "mercadolibre": {
                        "client_id": "1",
                        "client_secret": "s",
                        "access_token": "t",
                        "refresh_token": "r",
                    }
                }
            )
        )
        pub = MercadoLibrePublisher(auth_path=auth)
        assert pub.buscar_publicaciones("test") == []


# ===== Constants =====


class TestCategorias:
    def test_all_keys(self):
        assert "terreno" in CATEGORIAS
        assert "casa" in CATEGORIAS
        assert "campo" in CATEGORIAS
        assert "chacra" in CATEGORIAS
        assert "lote" in CATEGORIAS
        assert "construccion" in CATEGORIAS

    def test_terreno_is_MLA1459(self):
        assert CATEGORIAS["terreno"] == "MLA1459"
