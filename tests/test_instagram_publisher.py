"""Tests del modulo instagram_publisher.py.

Cubre:
  - ModoPublicacion: 3 valores del enum
  - PublicacionResultado: defaults, to_dict
  - InstagramPublisher._request: auth no configurado, HTTP error
  - _check_public_url: 200 OK, excepcion
  - publicar_foto: DRY_RUN, INTERACTIVO cancelado, REAL (upload falla, URL inaccesible, éxito, processing ERROR)
  - publicar_carrusel: <2, >10, DRY_RUN, REAL (upload falla, éxito, processing ERROR)
  - _confirmar: input True/False, EOFError
  - guardar_log: estructura del JSON
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from instagram_auth import AuthData, InstagramAuth
from instagram_publisher import (
    InstagramPublisher,
    ModoPublicacion,
    PublicacionResultado,
)


def _make_auth(tmp_path, token="tok123"):
    """Helper para crear InstagramAuth mock."""
    p = tmp_path / "auth.json"
    p.write_text(json.dumps({"access_token": token, "instagram_user_id": "uid"}))
    auth = InstagramAuth(p)
    auth.cargar()
    return auth


# ===== ModoPublicacion =====


class TestModoPublicacion:
    def test_valores(self):
        assert ModoPublicacion.DRY_RUN.value == "dry-run"
        assert ModoPublicacion.INTERACTIVO.value == "interactivo"
        assert ModoPublicacion.REAL.value == "real"

    def test_tres_modos(self):
        assert len(ModoPublicacion) == 3


# ===== PublicacionResultado =====


class TestPublicacionResultado:
    def test_defaults(self):
        r = PublicacionResultado(
            modo="dry-run", exito=False, tipo="foto", caption_length=10, n_imagenes=1
        )
        assert r.modo == "dry-run"
        assert r.exito is False
        assert r.media_ids == []
        assert r.instagram_post_id is None
        assert r.permalink is None
        assert r.error is None
        assert r.fecha != ""

    def test_to_dict(self):
        r = PublicacionResultado(
            modo="dry-run", exito=True, tipo="foto", caption_length=50, n_imagenes=1
        )
        d = r.to_dict()
        assert d["modo"] == "dry-run"
        assert d["exito"] is True
        assert isinstance(d, dict)


# ===== _request =====


class TestRequest:
    def test_auth_no_configurado(self, tmp_path):
        auth = InstagramAuth(tmp_path / "no.json")
        uploader = MagicMock()
        uploader.configurado = False
        publisher = InstagramPublisher(auth, uploader)
        with pytest.raises(RuntimeError, match="auth.json no configurado"):
            publisher._request("me")

    def test_get_exitoso(self, tmp_path):
        auth = _make_auth(tmp_path)
        uploader = MagicMock()
        publisher = InstagramPublisher(auth, uploader)

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": "123"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("instagram_publisher.urllib.request.urlopen", return_value=mock_resp):
            result = publisher._request("me")
        assert result == {"id": "123"}

    def test_post_exitoso(self, tmp_path):
        auth = _make_auth(tmp_path)
        uploader = MagicMock()
        publisher = InstagramPublisher(auth, uploader)

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": "456"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("instagram_publisher.urllib.request.urlopen", return_value=mock_resp):
            result = publisher._request("me/media", method="POST", json_body={"x": 1})
        assert result == {"id": "456"}

    def test_http_error_con_json(self, tmp_path):
        auth = _make_auth(tmp_path)
        uploader = MagicMock()
        publisher = InstagramPublisher(auth, uploader)

        err_body = json.dumps({"error": {"message": "Invalid token"}}).encode()
        mock_err = MagicMock()
        mock_err.read.return_value = err_body
        mock_err.code = 400

        with patch(
            "instagram_publisher.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("", 400, "Bad Request", {}, mock_err),
        ):
            with pytest.raises(RuntimeError, match="Graph API error 400"):
                publisher._request("me")

    def test_http_error_sin_json(self, tmp_path):
        auth = _make_auth(tmp_path)
        uploader = MagicMock()
        publisher = InstagramPublisher(auth, uploader)

        mock_err = MagicMock()
        mock_err.read.return_value = b"plain text error"

        with patch(
            "instagram_publisher.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("", 500, "Server Error", {}, mock_err),
        ):
            with pytest.raises(RuntimeError, match="Graph API error 500"):
                publisher._request("me")


# ===== _check_public_url =====


class TestCheckPublicUrl:
    def test_url_accesible(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("instagram_publisher.urllib.request.urlopen", return_value=mock_resp):
            assert publisher._check_public_url("https://example.com/img.jpg") is True

    def test_url_inaccesible(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        with patch(
            "instagram_publisher.urllib.request.urlopen",
            side_effect=Exception("timeout"),
        ):
            assert publisher._check_public_url("https://bad.url") is False


# ===== publicar_foto DRY_RUN =====


class TestPublicarFotoDryRun:
    def test_archivo_no_existe(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())
        result = publisher.publicar_foto(tmp_path / "no.jpg", "caption")
        assert result.exito is False
        assert "No existe" in result.error

    def test_dry_run(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        result = publisher.publicar_foto(img, "mi caption", modo=ModoPublicacion.DRY_RUN)
        assert result.exito is False
        assert result.metadata.get("dry_run") is True
        assert result.n_imagenes == 1

    def test_dry_run_con_hashtags(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        result = publisher.publicar_foto(
            img, "caption", hashtags=["#lote", "#venta"], modo=ModoPublicacion.DRY_RUN
        )
        assert result.exito is False
        assert result.n_imagenes == 1
        assert result.metadata.get("dry_run") is True


# ===== publicar_foto INTERACTIVO =====


class TestPublicarFotoInteractivo:
    def test_cancelado_por_usuario(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch("instagram_publisher.input", return_value="n"):
            result = publisher.publicar_foto(img, "caption", modo=ModoPublicacion.INTERACTIVO)
        assert result.exito is False
        assert "cancelado" in result.error


# ===== publicar_foto REAL =====


class TestPublicarFotoReal:
    def _make_publisher(self, tmp_path):
        auth = _make_auth(tmp_path)
        uploader = MagicMock()
        uploader.configurado = True
        uploader.subir.return_value = "https://res.cloudinary.com/test/image.jpg"
        publisher = InstagramPublisher(auth, uploader)
        return publisher

    def test_upload_falla(self, tmp_path):
        publisher = self._make_publisher(tmp_path)
        publisher.uploader.subir.return_value = None

        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch.object(publisher, "_check_public_url", return_value=True):
            result = publisher.publicar_foto(img, "cap", modo=ModoPublicacion.REAL)
        assert result.exito is False
        assert "subir la imagen" in result.error

    def test_url_inaccesible(self, tmp_path):
        publisher = self._make_publisher(tmp_path)

        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch.object(publisher, "_check_public_url", return_value=False):
            result = publisher.publicar_foto(img, "cap", modo=ModoPublicacion.REAL)
        assert result.exito is False
        assert "URL no accesible" in result.error

    def test_exito_con_permalink(self, tmp_path):
        publisher = self._make_publisher(tmp_path)

        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        container_resp = {"id": "container_123"}
        status_resp = {"status_code": "FINISHED"}
        publish_resp = {"id": "ig_post_456"}
        permalink_resp = {"permalink": "https://instagram.com/p/abc"}

        responses = [container_resp, status_resp, publish_resp, permalink_resp]
        call_count = [0]

        def mock_request(endpoint, method="GET", params=None, json_body=None):
            idx = call_count[0]
            call_count[0] += 1
            return responses[idx]

        with patch.object(publisher, "_check_public_url", return_value=True):
            with patch.object(publisher, "_request", side_effect=mock_request):
                with patch("instagram_publisher.time.sleep"):
                    result = publisher.publicar_foto(img, "cap", modo=ModoPublicacion.REAL)

        assert result.exito is True
        assert result.instagram_post_id == "ig_post_456"
        assert result.permalink == "https://instagram.com/p/abc"

    def test_processing_error(self, tmp_path):
        publisher = self._make_publisher(tmp_path)

        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        responses = [{"id": "c1"}, {"status_code": "ERROR"}]
        call_count = [0]

        def mock_request(endpoint, method="GET", params=None, json_body=None):
            idx = call_count[0]
            call_count[0] += 1
            return responses[idx]

        with patch.object(publisher, "_check_public_url", return_value=True):
            with patch.object(publisher, "_request", side_effect=mock_request):
                with patch("instagram_publisher.time.sleep"):
                    result = publisher.publicar_foto(img, "cap", modo=ModoPublicacion.REAL)

        assert result.exito is False
        assert "error" in result.error.lower()

    def test_graph_api_exception(self, tmp_path):
        publisher = self._make_publisher(tmp_path)

        img = tmp_path / "foto.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch.object(publisher, "_check_public_url", return_value=True):
            with patch.object(
                publisher, "_request", side_effect=RuntimeError("Graph API error 400")
            ):
                result = publisher.publicar_foto(img, "cap", modo=ModoPublicacion.REAL)

        assert result.exito is False
        assert "Graph API error" in result.error


# ===== publicar_carrusel =====


class TestPublicarCarrusel:
    def test_menos_de_2_imagenes(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        img = tmp_path / "a.jpg"
        img.write_bytes(b"data")

        result = publisher.publicar_carrusel([img], "cap", modo=ModoPublicacion.DRY_RUN)
        assert result.exito is False
        assert "2 y 10" in result.error

    def test_mas_de_10_imagenes(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        imgs = []
        for i in range(11):
            img = tmp_path / f"img{i}.jpg"
            img.write_bytes(b"data")
            imgs.append(img)

        result = publisher.publicar_carrusel(imgs, "cap", modo=ModoPublicacion.DRY_RUN)
        assert result.exito is False
        assert "2 y 10" in result.error

    def test_archivo_no_existe(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        result = publisher.publicar_carrusel(
            [tmp_path / "a.jpg", tmp_path / "b.jpg"], "cap", modo=ModoPublicacion.DRY_RUN
        )
        assert result.exito is False
        assert "No existe" in result.error

    def test_dry_run(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        imgs = []
        for i in range(2):
            img = tmp_path / f"img{i}.jpg"
            img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            imgs.append(img)

        result = publisher.publicar_carrusel(imgs, "cap", modo=ModoPublicacion.DRY_RUN)
        assert result.exito is False
        assert result.metadata.get("dry_run") is True
        assert result.n_imagenes == 2

    def test_real_exito(self, tmp_path):
        auth = _make_auth(tmp_path)
        uploader = MagicMock()
        uploader.configurado = True
        uploader.subir.return_value = "https://res.cloudinary.com/test/img.jpg"
        publisher = InstagramPublisher(auth, uploader)

        imgs = []
        for i in range(2):
            img = tmp_path / f"img{i}.jpg"
            img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            imgs.append(img)

        responses = [
            {"id": "child_1"},
            {"id": "child_2"},
            {"id": "carousel_container"},
            {"status_code": "FINISHED"},
            {"id": "ig_post_789"},
            {"permalink": "https://instagram.com/p/xyz"},
        ]
        call_count = [0]

        def mock_request(endpoint, method="GET", params=None, json_body=None):
            idx = call_count[0]
            call_count[0] += 1
            return responses[idx]

        with patch.object(publisher, "_check_public_url", return_value=True):
            with patch.object(publisher, "_request", side_effect=mock_request):
                with patch("instagram_publisher.time.sleep"):
                    result = publisher.publicar_carrusel(imgs, "cap", modo=ModoPublicacion.REAL)

        assert result.exito is True
        assert result.n_imagenes == 2
        assert result.instagram_post_id == "ig_post_789"

    def test_real_processing_error(self, tmp_path):
        auth = _make_auth(tmp_path)
        uploader = MagicMock()
        uploader.configurado = True
        uploader.subir.return_value = "https://res.cloudinary.com/test/img.jpg"
        publisher = InstagramPublisher(auth, uploader)

        imgs = []
        for i in range(2):
            img = tmp_path / f"img{i}.jpg"
            img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            imgs.append(img)

        responses = [
            {"id": "child_1"},
            {"id": "child_2"},
            {"id": "carousel_container"},
            {"status_code": "ERROR"},
        ]
        call_count = [0]

        def mock_request(endpoint, method="GET", params=None, json_body=None):
            idx = call_count[0]
            call_count[0] += 1
            return responses[idx]

        with patch.object(publisher, "_check_public_url", return_value=True):
            with patch.object(publisher, "_request", side_effect=mock_request):
                with patch("instagram_publisher.time.sleep"):
                    result = publisher.publicar_carrusel(imgs, "cap", modo=ModoPublicacion.REAL)

        assert result.exito is False

    def test_real_upload_falla_parcial(self, tmp_path):
        auth = _make_auth(tmp_path)
        uploader = MagicMock()
        uploader.configurado = True
        uploader.subir.side_effect = [None, "https://ok.com/img.jpg"]
        publisher = InstagramPublisher(auth, uploader)

        imgs = []
        for i in range(2):
            img = tmp_path / f"img{i}.jpg"
            img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
            imgs.append(img)

        result = publisher.publicar_carrusel(imgs, "cap", modo=ModoPublicacion.REAL)
        assert result.exito is False
        assert "subir" in result.error.lower()


# ===== _confirmar =====


class TestConfirmar:
    def test_si(self):
        with patch("instagram_publisher.input", return_value="s"):
            assert InstagramPublisher._confirmar("¿Seguro?") is True

    def test_si_long(self):
        with patch("instagram_publisher.input", return_value="si"):
            assert InstagramPublisher._confirmar("¿Seguro?") is True

    def test_no(self):
        with patch("instagram_publisher.input", return_value="n"):
            assert InstagramPublisher._confirmar("¿Seguro?") is False

    def test_vacio(self):
        with patch("instagram_publisher.input", return_value=""):
            assert InstagramPublisher._confirmar("¿Seguro?") is False

    def test_eoferror(self):
        with patch("instagram_publisher.input", side_effect=EOFError):
            assert InstagramPublisher._confirmar("¿Seguro?") is False


# ===== guardar_log =====


class TestGuardarLog:
    def test_guardar_log(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        resultado = PublicacionResultado(
            modo="dry-run",
            exito=True,
            tipo="foto",
            caption_length=100,
            n_imagenes=1,
        )

        with patch("instagram_publisher.LOG_DIR", tmp_path):
            ruta = publisher.guardar_log(resultado, nombre="test_log")

        assert ruta.exists()
        data = json.loads(ruta.read_text())
        assert data["modo"] == "dry-run"
        assert data["exito"] is True

    def test_guardar_log_nombre_auto(self, tmp_path):
        auth = _make_auth(tmp_path)
        publisher = InstagramPublisher(auth, MagicMock())

        resultado = PublicacionResultado(
            modo="real",
            exito=True,
            tipo="carrusel",
            caption_length=50,
            n_imagenes=3,
        )

        with patch("instagram_publisher.LOG_DIR", tmp_path):
            ruta = publisher.guardar_log(resultado)

        assert ruta.exists()
        assert "publicacion_" in ruta.name
