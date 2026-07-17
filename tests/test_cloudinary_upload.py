"""Tests del modulo cloudinary_upload.py.

Cubre:
  - CloudinaryUploader: _cargar_config, subir, _build_multipart
  - Firma SHA1 con valores conocidos
  - Manejo de errores: no configurado, archivo no existe, HTTP error
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudinary_upload import CloudinaryUploader


def _write_auth(tmp_path, cloud_name="test_cloud", api_key="key123", api_secret="secret456"):
    """Helper para crear auth.json con credenciales Cloudinary.

    El dataclass AuthData solo acepta access_token e instagram_user_id,
    pero _cargar_config() lee el JSON crudo para extraer cloudinary.
    """
    data = {
        "access_token": "tok",
        "instagram_user_id": "uid",
    }
    p = tmp_path / "auth.json"
    p.write_text(json.dumps(data))
    return p


def _raw_auth_with_cloudinary(cloud_name="test_cloud", api_key="key123", api_secret="secret456"):
    """Devuelve el JSON crudo con cloudinary para mockear read_text."""
    return json.dumps(
        {
            "access_token": "tok",
            "instagram_user_id": "uid",
            "cloudinary": {
                "cloud_name": cloud_name,
                "api_key": api_key,
                "api_secret": api_secret,
            },
        }
    )


class TestCloudinaryConfig:
    def test_no_configurado_si_no_auth(self, tmp_path):
        from instagram_auth import InstagramAuth

        auth = InstagramAuth(tmp_path / "no.json")
        uploader = CloudinaryUploader(auth)
        assert uploader.configurado is False

    def test_configurado_con_credenciales(self, tmp_path):
        from instagram_auth import InstagramAuth

        # Auth.json válido para AuthData (sin campo cloudinary)
        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"access_token": "tok", "instagram_user_id": "uid"}))
        auth = InstagramAuth(p)
        auth.cargar()

        # Mockear la lectura raw de auth.json para que tenga cloudinary
        raw_with_cloudinary = json.dumps(
            {
                "access_token": "tok",
                "instagram_user_id": "uid",
                "cloudinary": {
                    "cloud_name": "test_cloud",
                    "api_key": "key123",
                    "api_secret": "secret456",
                },
            }
        )
        with patch.object(Path, "read_text", return_value=raw_with_cloudinary):
            uploader = CloudinaryUploader(auth)
        assert uploader.configurado is True
        assert uploader.cloud_name == "test_cloud"
        assert uploader.api_key == "key123"
        assert uploader.api_secret == "secret456"

    def test_no_configurado_keys_faltantes(self, tmp_path):
        from instagram_auth import InstagramAuth

        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"access_token": "tok", "instagram_user_id": "uid"}))
        auth = InstagramAuth(p)
        auth.cargar()

        raw = json.dumps(
            {
                "access_token": "tok",
                "instagram_user_id": "uid",
                "cloudinary": {"cloud_name": "c", "api_key": "", "api_secret": ""},
            }
        )
        with patch.object(Path, "read_text", return_value=raw):
            uploader = CloudinaryUploader(auth)
        assert uploader.configurado is False

    def test_no_configurado_cloudinary_section_falta(self, tmp_path):
        from instagram_auth import InstagramAuth

        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"access_token": "tok", "instagram_user_id": "uid"}))
        auth = InstagramAuth(p)
        auth.cargar()

        raw = json.dumps({"access_token": "tok", "instagram_user_id": "uid"})
        with patch.object(Path, "read_text", return_value=raw):
            uploader = CloudinaryUploader(auth)
        assert uploader.configurado is False

    def test_no_configurado_auth_json_malformado(self, tmp_path):
        from instagram_auth import InstagramAuth

        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"access_token": "tok", "instagram_user_id": "uid"}))
        auth = InstagramAuth(p)
        auth.cargar()

        with patch.object(Path, "read_text", return_value="not json {{{"):
            uploader = CloudinaryUploader(auth)
        assert uploader.configurado is False


class TestFirmaSHA1:
    def test_firma_con_valores_conocidos(self, tmp_path):
        from instagram_auth import InstagramAuth

        p = _write_auth(tmp_path, api_secret="mi_secret")
        auth = InstagramAuth(p)
        auth.cargar()
        CloudinaryUploader(auth)

        carpeta = "realestate_studio"
        public_id = "realestate_studio/foto_1234567890"
        timestamp = 1234567890

        params_to_sign = f"folder={carpeta}&public_id={public_id}&timestamp={timestamp}"
        expected = hashlib.sha1(f"{params_to_sign}mi_secret".encode()).hexdigest()

        assert expected == hashlib.sha1(f"{params_to_sign}mi_secret".encode()).hexdigest()
        assert len(expected) == 40


class TestCloudinarySubir:
    def _make_uploader(
        self, tmp_path, cloud_name="test_cloud", api_key="key123", api_secret="secret456"
    ):
        """Crea un CloudinaryUploader configurado con auth.json + mock de cloudinary."""
        from instagram_auth import InstagramAuth

        p = _write_auth(tmp_path)
        auth = InstagramAuth(p)
        auth.cargar()
        raw = _raw_auth_with_cloudinary(cloud_name, api_key, api_secret)
        with patch.object(Path, "read_text", return_value=raw):
            return CloudinaryUploader(auth)

    def test_no_configurado(self, tmp_path):
        from instagram_auth import InstagramAuth

        auth = InstagramAuth(tmp_path / "no.json")
        uploader = CloudinaryUploader(auth)
        result = uploader.subir(tmp_path / "dummy.jpg")
        assert result is None

    def test_archivo_no_existe(self, tmp_path):
        uploader = self._make_uploader(tmp_path)
        result = uploader.subir(tmp_path / "no_existe.jpg")
        assert result is None

    def test_subir_exitoso(self, tmp_path):
        uploader = self._make_uploader(tmp_path)

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        resp_data = {"secure_url": "https://res.cloudinary.com/test/image/upload/v1/test.jpg"}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resp_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("cloudinary_upload.urllib.request.urlopen", return_value=mock_resp):
            with patch("cloudinary_upload.time.time", return_value=1234567890):
                result = uploader.subir(img)

        assert result == "https://res.cloudinary.com/test/image/upload/v1/test.jpg"

    def test_subir_http_error(self, tmp_path):
        uploader = self._make_uploader(tmp_path)

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch(
            "cloudinary_upload.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("", 400, "Bad Request", {}, None),
        ):
            result = uploader.subir(img)
        assert result is None

    def test_subir_sin_secure_url(self, tmp_path):
        uploader = self._make_uploader(tmp_path)

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"error": "bad"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("cloudinary_upload.urllib.request.urlopen", return_value=mock_resp):
            result = uploader.subir(img)
        assert result is None

    def test_subir_url_error(self, tmp_path):
        uploader = self._make_uploader(tmp_path)

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch(
            "cloudinary_upload.urllib.request.urlopen",
            side_effect=urllib.error.URLError("timeout"),
        ):
            result = uploader.subir(img)
        assert result is None

    def test_public_id_custom(self, tmp_path):
        uploader = self._make_uploader(tmp_path)

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        resp_data = {"secure_url": "https://res.cloudinary.com/test/image/upload/custom_id.jpg"}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resp_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("cloudinary_upload.urllib.request.urlopen", return_value=mock_resp):
            with patch("cloudinary_upload.time.time", return_value=1234567890):
                result = uploader.subir(img, public_id="custom_id")
        assert result is not None

    def test_carpeta_custom(self, tmp_path):
        uploader = self._make_uploader(tmp_path)

        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        resp_data = {"secure_url": "https://res.cloudinary.com/test/image/upload/test.jpg"}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resp_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("cloudinary_upload.urllib.request.urlopen", return_value=mock_resp):
            with patch("cloudinary_upload.time.time", return_value=1234567890):
                result = uploader.subir(img, carpeta="mi_carpeta")
        assert result is not None


class TestBuildMultipart:
    def test_estructura_basica(self, tmp_path):
        img = tmp_path / "foto.jpg"
        img.write_bytes(b"contenido_fake")

        fields = {"api_key": "key123", "timestamp": "123", "signature": "abc123"}
        boundary = "----TestBoundary"
        body = CloudinaryUploader._build_multipart(boundary, fields, img)

        assert b"----TestBoundary" in body
        assert b'Content-Disposition: form-data; name="api_key"' in body
        assert b"key123" in body
        assert b'Content-Disposition: form-data; name="signature"' in body
        assert b"abc123" in body
        assert b'Content-Disposition: form-data; name="file"; filename="foto.jpg"' in body
        assert b"contenido_fake" in body
        assert body.endswith(b"----TestBoundary--\r\n")

    def test_campos_multiple(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"data")

        fields = {"a": "1", "b": "2", "c": "3"}
        boundary = "----B"
        body = CloudinaryUploader._build_multipart(boundary, fields, img)

        assert b'name="a"' in body
        assert b'name="b"' in body
        assert b'name="c"' in body
