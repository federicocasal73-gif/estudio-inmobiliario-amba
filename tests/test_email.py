"""Tests del modulo email_notifier.py.

Cubre:
  - EmailMessage: dataclass
  - EmailResult: resumen
  - EmailNotifier: configurado, enviar, alerta_lead, reporte_semanal, alerta_error
"""

from __future__ import annotations

import json
import smtplib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from email_notifier import (
    EmailMessage,
    EmailNotifier,
    EmailResult,
)


def _write_auth(data: dict, path: Path) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class TestEmailMessage:
    def test_defaults(self):
        msg = EmailMessage(to=["a@test.com"], subject="Hola")
        assert msg.body_text == ""
        assert msg.body_html == ""
        assert msg.cc == []
        assert msg.bcc == []

    def test_with_all_fields(self):
        msg = EmailMessage(
            to=["a@test.com"],
            subject="Test",
            body_text="Plain text",
            body_html="<h1>HTML</h1>",
            from_name="Test Studio",
            cc=["b@test.com"],
            bcc=["c@test.com"],
        )
        assert len(msg.to) == 1
        assert len(msg.cc) == 1
        assert len(msg.bcc) == 1


class TestEmailResult:
    def test_resumen_ok(self):
        r = EmailResult(ok=True, recipients=["a@test.com", "b@test.com"])
        assert "2" in r.resumen()
        assert "enviado" in r.resumen()

    def test_resumen_error(self):
        r = EmailResult(ok=False, error="SMTP timeout")
        assert "SMTP timeout" in r.resumen()


class TestEmailNotifier:
    def test_no_configurado_sin_auth(self, tmp_path):
        notifier = EmailNotifier(auth_path=tmp_path / "no_existe.json")
        assert notifier.configurado() is False

    def test_configurado_con_auth(self, tmp_path):
        _write_auth(
            {
                "email": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "test@gmail.com",
                    "password": "app_pass",
                    "to_addresses": ["admin@test.com"],
                }
            },
            tmp_path / "auth.json",
        )
        notifier = EmailNotifier(auth_path=tmp_path / "auth.json")
        assert notifier.configurado() is True

    def test_enviar_falla_sin_config(self, tmp_path):
        notifier = EmailNotifier(auth_path=tmp_path / "no_existe.json")
        result = notifier.enviar(EmailMessage(to=["a@b.com"], subject="Test"))
        assert result.ok is False
        assert "configurado" in result.error.lower()

    def test_enviar_falla_sin_destinatarios(self, tmp_path):
        _write_auth(
            {
                "email": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "test@gmail.com",
                    "password": "app_pass",
                    "to_addresses": [],
                }
            },
            tmp_path / "auth.json",
        )
        notifier = EmailNotifier(auth_path=tmp_path / "auth.json")
        result = notifier.enviar(EmailMessage(to=[], subject="Test"))
        assert result.ok is False
        assert "destinatarios" in result.error.lower()

    def test_alerta_lead_falla_sin_config(self, tmp_path):
        notifier = EmailNotifier(auth_path=tmp_path / "no_existe.json")
        result = notifier.enviar_alerta_lead(
            cliente="Juan",
            mensaje="Quiere precio",
            propiedad="Chacra 5ha",
        )
        assert result.ok is False

    def test_reporte_semanal_falla_sin_config(self, tmp_path):
        notifier = EmailNotifier(auth_path=tmp_path / "no_existe.json")
        result = notifier.enviar_reporte_semanal(
            posts_publicados=5,
            leads_nuevos=12,
        )
        assert result.ok is False

    def test_alerta_error_falla_sin_config(self, tmp_path):
        notifier = EmailNotifier(auth_path=tmp_path / "no_existe.json")
        result = notifier.enviar_alerta_error(
            modulo="test",
            error="Something broke",
        )
        assert result.ok is False

    def test_mock_enviar_exito(self, tmp_path):
        _write_auth(
            {
                "email": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "test@gmail.com",
                    "password": "app_pass",
                    "to_addresses": ["admin@test.com"],
                }
            },
            tmp_path / "auth.json",
        )
        notifier = EmailNotifier(auth_path=tmp_path / "auth.json")

        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)
        with patch("smtplib.SMTP", return_value=mock_server):
            result = notifier.enviar(
                EmailMessage(to=["admin@test.com"], subject="Test", body_text="Hello")
            )
            assert result.ok is True
            assert "admin@test.com" in result.recipients
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.sendmail.assert_called_once()

    def test_alerta_lead_con_mock(self, tmp_path):
        _write_auth(
            {
                "email": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "test@gmail.com",
                    "password": "app_pass",
                    "to_addresses": ["admin@test.com"],
                }
            },
            tmp_path / "auth.json",
        )
        notifier = EmailNotifier(auth_path=tmp_path / "auth.json")

        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)
        with patch("smtplib.SMTP", return_value=mock_server):
            result = notifier.enviar_alerta_lead(
                cliente="Juan Perez",
                mensaje="Quiere precio de Chacra 5ha",
                propiedad="Chacra 5 ha en Cañuelas",
            )
            assert result.ok is True
            mock_server.sendmail.assert_called_once()

    def test_reporte_semanal_con_mock(self, tmp_path):
        _write_auth(
            {
                "email": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "test@gmail.com",
                    "password": "app_pass",
                    "to_addresses": ["admin@test.com"],
                }
            },
            tmp_path / "auth.json",
        )
        notifier = EmailNotifier(auth_path=tmp_path / "auth.json")

        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)
        with patch("smtplib.SMTP", return_value=mock_server):
            result = notifier.enviar_reporte_semanal(
                posts_publicados=5,
                leads_nuevos=12,
                mejor_post="Chacra en Cañuelas (15% engagement)",
                propiedades_activas=8,
            )
            assert result.ok is True

    def test_alerta_error_con_mock(self, tmp_path):
        _write_auth(
            {
                "email": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "test@gmail.com",
                    "password": "app_pass",
                    "to_addresses": ["admin@test.com"],
                }
            },
            tmp_path / "auth.json",
        )
        notifier = EmailNotifier(auth_path=tmp_path / "auth.json")

        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)
        with patch("smtplib.SMTP", return_value=mock_server):
            result = notifier.enviar_alerta_error(
                modulo="generation_pipeline",
                error="Fooocus timeout after 600s",
                contexto="Generando imagen para Chacra 5ha",
            )
            assert result.ok is True
