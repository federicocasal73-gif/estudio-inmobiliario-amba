"""Tests para email_notifier.py - Notificador por email via SMTP."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from email_notifier import EmailMessage, EmailResult, EmailNotifier


class TestEmailMessage:
    def test_creation(self):
        msg = EmailMessage(to=["a@b.com"], subject="Test")
        assert msg.to == ["a@b.com"]
        assert msg.subject == "Test"
        assert msg.body_text == ""
        assert msg.body_html == ""
        assert msg.from_name == "Estudio Inmobiliario AMBA"
        assert msg.cc == []
        assert msg.bcc == []

    def test_creation_with_all_fields(self):
        msg = EmailMessage(
            to=["a@b.com"],
            subject="Test",
            body_text="plain",
            body_html="<h1>html</h1>",
            from_name="Custom",
            cc=["c@d.com"],
            bcc=["e@f.com"],
        )
        assert msg.from_name == "Custom"
        assert msg.cc == ["c@d.com"]
        assert msg.bcc == ["e@f.com"]


class TestEmailResult:
    def test_ok_result(self):
        r = EmailResult(ok=True, recipients=["a@b.com"])
        assert r.ok is True
        assert r.resumen() == "Email enviado a 1 destinatarios"

    def test_ok_multiple_recipients(self):
        r = EmailResult(ok=True, recipients=["a@b.com", "c@d.com"])
        assert r.resumen() == "Email enviado a 2 destinatarios"

    def test_error_result(self):
        r = EmailResult(ok=False, error="SMTP failed")
        assert r.ok is False
        assert "SMTP failed" in r.resumen()

    def test_error_no_recipients(self):
        r = EmailResult(ok=False, error="timeout")
        assert r.resumen() == "Error enviando email: timeout"


class TestEmailNotifier:
    def _make_auth(self, tmp_path: Path, config: dict | None = None) -> Path:
        auth = tmp_path / "auth.json"
        data = config or {
            "email": {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "test@gmail.com",
                "password": "app_password",
                "from_name": "Test",
                "to_addresses": ["admin@test.com"],
            }
        }
        auth.write_text(json.dumps(data), encoding="utf-8")
        return auth

    def test_init_with_config(self, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        assert n.configurado() is True

    def test_init_without_config(self, tmp_path):
        auth = tmp_path / "nonexistent.json"
        n = EmailNotifier(auth_path=auth)
        assert n.configurado() is False

    def test_init_with_empty_email_section(self, tmp_path):
        auth = self._make_auth(tmp_path, config={"email": {}})
        n = EmailNotifier(auth_path=auth)
        assert n.configurado() is False

    def test_init_with_invalid_json(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text("not json {{{")
        n = EmailNotifier(auth_path=auth)
        assert n.configurado() is False

    def test_enviar_no_configurado(self, tmp_path):
        n = EmailNotifier(auth_path=tmp_path / "no.json")
        result = n.enviar(EmailMessage(to=["a@b.com"], subject="Test"))
        assert result.ok is False
        assert "configurado" in result.error.lower()

    def test_enviar_no_destinatarios(self, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        result = n.enviar(EmailMessage(to=[], subject="Test"))
        assert result.ok is False
        assert "destinatarios" in result.error.lower()

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_success(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = n.enviar(EmailMessage(to=["a@b.com"], subject="Test", body_text="Hola"))
        assert result.ok is True
        assert "a@b.com" in result.recipients
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_con_cc_y_bcc(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        msg = EmailMessage(
            to=["a@b.com"],
            subject="Test",
            cc=["c@d.com"],
            bcc=["e@f.com"],
        )
        result = n.enviar(msg)
        assert result.ok is True
        assert len(result.recipients) == 3

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_smtp_error(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_smtp.side_effect = Exception("Connection refused")

        result = n.enviar(EmailMessage(to=["a@b.com"], subject="Test"))
        assert result.ok is False
        assert "Connection refused" in result.error

    @patch("email_notifier.smtplib.SMTP")
    def test_build_mime_with_html(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        msg = EmailMessage(
            to=["a@b.com"],
            subject="Test",
            body_text="plain",
            body_html="<h1>HTML</h1>",
        )
        mime = n._build_mime(msg)
        assert "a@b.com" in mime["To"]
        assert "Test" in mime["Subject"]

    @patch("email_notifier.smtplib.SMTP")
    def test_build_mime_with_cc(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        msg = EmailMessage(to=["a@b.com"], subject="T", cc=["c@d.com"])
        mime = n._build_mime(msg)
        assert "c@d.com" in mime["Cc"]

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_alerta_lead(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = n.enviar_alerta_lead(
            cliente="Juan Perez",
            mensaje="Quiere precio",
            propiedad="Chacra 5ha",
        )
        assert result.ok is True

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_alerta_lead_sin_propiedad(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = n.enviar_alerta_lead(cliente="Juan", mensaje="Hola")
        assert result.ok is True

    def test_enviar_alerta_lead_no_destinatarios(self, tmp_path):
        auth = self._make_auth(tmp_path, config={"email": {"smtp_host": "smtp.test.com"}})
        n = EmailNotifier(auth_path=auth)
        result = n.enviar_alerta_lead(cliente="Juan", mensaje="Hola")
        assert result.ok is False

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_reporte_semanal(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = n.enviar_reporte_semanal(
            posts_publicados=5,
            leads_nuevos=12,
            mejor_post="Chacra Canuelas",
            propiedades_activas=8,
            errores=["Error 1", "Error 2"],
        )
        assert result.ok is True

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_reporte_sin_errores(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = n.enviar_reporte_semanal(posts_publicados=3)
        assert result.ok is True

    def test_enviar_reporte_no_destinatarios(self, tmp_path):
        auth = self._make_auth(tmp_path, config={"email": {"smtp_host": "smtp.test.com"}})
        n = EmailNotifier(auth_path=auth)
        result = n.enviar_reporte_semanal()
        assert result.ok is False

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_alerta_error(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = n.enviar_alerta_error(
            modulo="studio",
            error="Connection timeout",
            contexto="Generando carrusel",
        )
        assert result.ok is True

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_alerta_error_sin_contexto(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        result = n.enviar_alerta_error(modulo="test", error="fail")
        assert result.ok is True

    def test_enviar_alerta_error_no_destinatarios(self, tmp_path):
        auth = self._make_auth(tmp_path, config={"email": {"smtp_host": "smtp.test.com"}})
        n = EmailNotifier(auth_path=auth)
        result = n.enviar_alerta_error(modulo="test", error="fail")
        assert result.ok is False

    def test_cargar_config_missing_email_key(self, tmp_path):
        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({"other_key": {}}))
        n = EmailNotifier(auth_path=auth)
        assert n.configurado() is False

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_text_only(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        msg = EmailMessage(to=["a@b.com"], subject="T", body_text="Solo texto")
        result = n.enviar(msg)
        assert result.ok is True

    @patch("email_notifier.smtplib.SMTP")
    def test_enviar_html_only(self, mock_smtp, tmp_path):
        auth = self._make_auth(tmp_path)
        n = EmailNotifier(auth_path=auth)
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        msg = EmailMessage(to=["a@b.com"], subject="T", body_html="<p>Hola</p>")
        result = n.enviar(msg)
        assert result.ok is True


class TestEmailNotifierMain:
    def test_main_block(self, tmp_path, capsys):
        from email_notifier import EmailNotifier as EN

        auth = tmp_path / "auth.json"
        auth.write_text(json.dumps({"email": {"smtp_host": "smtp.test.com"}}))

        with patch.object(EN, "__init__", lambda self, auth_path=None: setattr(self, "_config", {"smtp_host": "x"}) or setattr(self, "auth_path", auth or tmp_path / "x")):
            n = EN.__new__(EN)
            n._config = {"smtp_host": "smtp.test.com"}
            assert n.configurado() is True

        n2 = EN.__new__(EN)
        n2._config = {}
        assert n2.configurado() is False
