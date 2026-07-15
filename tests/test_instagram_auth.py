"""Tests del modulo instagram_auth.py.

Cubre:
  - AuthData dataclass: to_dict, campos default
  - InstagramAuth: configurado, cargar, guardar, data property
  - validar_token: token valido, expirado, URLError, sin auth
  - validar_permisos_instagram: todos granted, faltantes, HTTP error
  - info_cuenta: OK, URLError, sin auth
  - crear_auth_example_si_no_existe
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from instagram_auth import (
    AuthData,
    InstagramAuth,
    crear_auth_example_si_no_existe,
)


class TestAuthData:
    def test_campos_obligatorios(self):
        auth = AuthData(access_token="tok", instagram_user_id="123")
        assert auth.access_token == "tok"
        assert auth.instagram_user_id == "123"

    def test_defaults(self):
        auth = AuthData(access_token="tok", instagram_user_id="123")
        assert auth.username == ""
        assert auth.app_id == ""
        assert auth.expires_at == ""

    def test_to_dict(self):
        auth = AuthData(access_token="tok", instagram_user_id="123", username="testuser")
        d = auth.to_dict()
        assert d["access_token"] == "tok"
        assert d["instagram_user_id"] == "123"
        assert d["username"] == "testuser"
        assert len(d) == 5


class TestInstagramAuthConfig:
    def test_no_configurado_si_no_existe(self, tmp_path):
        auth = InstagramAuth(tmp_path / "no_existe.json")
        assert auth.configurado() is False

    def test_configurado_si_existe(self, tmp_path):
        p = tmp_path / "auth.json"
        p.write_text("{}")
        auth = InstagramAuth(p)
        assert auth.configurado() is True

    def test_cargar_json_valido(self, tmp_path):
        p = tmp_path / "auth.json"
        data = {"access_token": "tok123", "instagram_user_id": "456"}
        p.write_text(json.dumps(data))
        auth = InstagramAuth(p)
        result = auth.cargar()
        assert result is not None
        assert result.access_token == "tok123"
        assert result.instagram_user_id == "456"

    def test_cargar_no_configurado(self, tmp_path):
        auth = InstagramAuth(tmp_path / "no_existe.json")
        result = auth.cargar()
        assert result is None

    def test_cargar_json_malformado(self, tmp_path):
        p = tmp_path / "auth.json"
        p.write_text("esto no es json {{{")
        auth = InstagramAuth(p)
        result = auth.cargar()
        assert result is None

    def test_cargar_campos_faltantes(self, tmp_path):
        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"access_token": "tok"}))
        auth = InstagramAuth(p)
        result = auth.cargar()
        assert result is None

    def test_guardar_y_cargar(self, tmp_path):
        p = tmp_path / "auth.json"
        auth = InstagramAuth(p)
        data = AuthData(access_token="tok", instagram_user_id="123", username="u")
        auth.guardar(data)
        assert p.exists()
        loaded = auth.cargar()
        assert loaded is not None
        assert loaded.access_token == "tok"

    def test_guardar_permisos_600(self, tmp_path):
        p = tmp_path / "auth.json"
        auth = InstagramAuth(p)
        auth.guardar(AuthData(access_token="t", instagram_user_id="1"))
        mode = p.stat().st_mode & 0o777
        assert mode == 0o600

    def test_guardar_chmod_falla_silencioso(self, tmp_path):
        p = tmp_path / "auth.json"
        auth = InstagramAuth(p)
        with patch.object(Path, "chmod", side_effect=OSError("perm denied")):
            auth.guardar(AuthData(access_token="t", instagram_user_id="1"))
        assert p.exists()


class TestInstagramAuthDataProperty:
    def test_lazy_load(self, tmp_path):
        p = tmp_path / "auth.json"
        data = {"access_token": "tok", "instagram_user_id": "123"}
        p.write_text(json.dumps(data))
        auth = InstagramAuth(p)
        assert auth._data is None
        d = auth.data
        assert d is not None
        assert d.access_token == "tok"
        assert auth._data is d

    def test_data_none_si_no_existe(self, tmp_path):
        auth = InstagramAuth(tmp_path / "no.json")
        assert auth.data is None


class TestValidarToken:
    def _make_auth(self, tmp_path, token="tok123"):
        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"access_token": token, "instagram_user_id": "uid"}))
        auth = InstagramAuth(p)
        auth.cargar()
        return auth

    def test_token_valido(self, tmp_path):
        auth = self._make_auth(tmp_path)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("instagram_auth.urllib.request.urlopen", return_value=mock_resp):
            assert auth.validar_token() is True

    def test_token_invalido_http_error(self, tmp_path):
        auth = self._make_auth(tmp_path)
        with patch(
            "instagram_auth.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("", 400, "Bad Request", {}, None),
        ):
            assert auth.validar_token() is False

    def test_token_url_error(self, tmp_path):
        auth = self._make_auth(tmp_path)
        with patch(
            "instagram_auth.urllib.request.urlopen",
            side_effect=urllib.error.URLError("timeout"),
        ):
            assert auth.validar_token() is False

    def test_token_sin_auth(self, tmp_path):
        auth = InstagramAuth(tmp_path / "no.json")
        assert auth.validar_token() is False


class TestValidarPermisos:
    def _make_auth(self, tmp_path):
        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"access_token": "tok", "instagram_user_id": "uid"}))
        auth = InstagramAuth(p)
        auth.cargar()
        return auth

    def test_todos_los_permisos(self, tmp_path):
        auth = self._make_auth(tmp_path)
        resp_data = {
            "data": [
                {"permission": "instagram_basic", "status": "granted"},
                {"permission": "instagram_content_publish", "status": "granted"},
                {"permission": "pages_show_list", "status": "granted"},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resp_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("instagram_auth.urllib.request.urlopen", return_value=mock_resp):
            ok, faltan = auth.validar_permisos_instagram()
        assert ok is True
        assert faltan == []

    def test_permisos_faltantes(self, tmp_path):
        auth = self._make_auth(tmp_path)
        resp_data = {"data": [{"permission": "instagram_basic", "status": "granted"}]}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(resp_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("instagram_auth.urllib.request.urlopen", return_value=mock_resp):
            ok, faltan = auth.validar_permisos_instagram()
        assert ok is False
        assert "instagram_content_publish" in faltan

    def test_http_error(self, tmp_path):
        auth = self._make_auth(tmp_path)
        with patch(
            "instagram_auth.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("", 400, "err", {}, None),
        ):
            ok, faltan = auth.validar_permisos_instagram()
        assert ok is False
        assert len(faltan) == 1
        assert "HTTP error" in faltan[0]

    def test_sin_auth(self, tmp_path):
        auth = InstagramAuth(tmp_path / "no.json")
        ok, faltan = auth.validar_permisos_instagram()
        assert ok is False
        assert faltan == []


class TestInfoCuenta:
    def _make_auth(self, tmp_path):
        p = tmp_path / "auth.json"
        p.write_text(json.dumps({"access_token": "tok", "instagram_user_id": "uid"}))
        auth = InstagramAuth(p)
        auth.cargar()
        return auth

    def test_info_ok(self, tmp_path):
        auth = self._make_auth(tmp_path)
        info = {"id": "uid", "username": "testuser", "followers_count": 100}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(info).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("instagram_auth.urllib.request.urlopen", return_value=mock_resp):
            result = auth.info_cuenta()
        assert result is not None
        assert result["username"] == "testuser"

    def test_info_url_error(self, tmp_path):
        auth = self._make_auth(tmp_path)
        with patch(
            "instagram_auth.urllib.request.urlopen",
            side_effect=urllib.error.URLError("no red"),
        ):
            assert auth.info_cuenta() is None

    def test_info_http_error(self, tmp_path):
        auth = self._make_auth(tmp_path)
        with patch(
            "instagram_auth.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("", 404, "Not Found", {}, None),
        ):
            assert auth.info_cuenta() is None

    def test_info_sin_auth(self, tmp_path):
        auth = InstagramAuth(tmp_path / "no.json")
        assert auth.info_cuenta() is None


class TestCrearAuthExample:
    def test_no_imprime_si_auth_existe(self, tmp_path, capsys):
        with patch("instagram_auth.AUTH_FILE", tmp_path / "auth.json"):
            (tmp_path / "auth.json").write_text("{}")
            with patch("instagram_auth.AUTH_EXAMPLE", tmp_path / "auth-example.json"):
                crear_auth_example_si_no_existe()
        captured = capsys.readouterr()
        assert "INFO" not in captured.out

    def test_imprime_si_no_existe_auth(self, tmp_path, capsys):
        (tmp_path / "auth-example.json").write_text("{}")
        with patch("instagram_auth.AUTH_FILE", tmp_path / "auth.json"):
            with patch("instagram_auth.AUTH_EXAMPLE", tmp_path / "auth-example.json"):
                crear_auth_example_si_no_existe()
        captured = capsys.readouterr()
        assert "INFO" in captured.out

    def test_no_imprime_si_tampoco_existe_example(self, tmp_path, capsys):
        with patch("instagram_auth.AUTH_FILE", tmp_path / "auth.json"):
            with patch("instagram_auth.AUTH_EXAMPLE", tmp_path / "no_existe.json"):
                crear_auth_example_si_no_existe()
        captured = capsys.readouterr()
        assert "INFO" not in captured.out
