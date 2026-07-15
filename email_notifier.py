"""
Notificador por email para leads, alertas y reportes.

Soporta:
  - Alertas de leads nuevos (cuando alguien consulta por una propiedad)
  - Reportes semanales de actividad
  - Alertas de publicaciones programadas
  - Notificaciones de errores

Envia via SMTP (Gmail, Outlook, o cualquier servidor SMTP).

Setup:
  1. Configurar servidor SMTP (Gmail: smtp.gmail.com:587)
  2. Usar App Password (no la password normal de Gmail)
  3. Agregar a auth.json:
       "email": {
         "smtp_host": "smtp.gmail.com",
         "smtp_port": 587,
         "username": "tu@gmail.com",
         "password": "app_password_de_gmail",
         "from_name": "Estudio Inmobiliario AMBA",
         "to_addresses": ["admin@tudominio.com", "otro@email.com"]
       }

Uso:
    from email_notifier import EmailNotifier

    notifier = EmailNotifier()
    notifier.enviar_alerta_lead(
        cliente="Juan Perez",
        mensaje="Quiere saber precio de Chacra 5ha",
        propiedad="Chacra 5 ha en Cañuelas",
    )
    notifier.enviar_reporte_semanal(
        posts_publicados=5,
        leads_nuevos=12,
        mejor_post="Chacra en Cañuelas (15% engagement)",
    )
"""

from __future__ import annotations

import json
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
AUTH_PATH = ROOT / "auth.json"


@dataclass
class EmailMessage:
    """Mensaje de email."""

    to: list[str]
    subject: str
    body_text: str = ""
    body_html: str = ""
    from_name: str = "Estudio Inmobiliario AMBA"
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)


@dataclass
class EmailResult:
    """Resultado de envio de email."""

    ok: bool
    error: str | None = None
    recipients: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        if self.ok:
            return f"Email enviado a {len(self.recipients)} destinatarios"
        else:
            return f"Error enviando email: {self.error}"


class EmailNotifier:
    """Envia notificaciones por email via SMTP."""

    def __init__(self, auth_path: Path | None = None):
        self.auth_path = auth_path or AUTH_PATH
        self._config: dict[str, Any] = {}
        self._cargar_config()

    def _cargar_config(self) -> bool:
        try:
            raw = json.loads(self.auth_path.read_text(encoding="utf-8"))
            self._config = raw.get("email", {})
            return bool(self._config.get("smtp_host"))
        except (json.JSONDecodeError, OSError):
            return False

    def configurado(self) -> bool:
        return bool(self._config.get("smtp_host"))

    def _build_mime(self, msg: EmailMessage) -> MIMEMultipart:
        """Construye el email MIME."""
        mime = MIMEMultipart("alternative")
        mime["From"] = f"{msg.from_name} <{self._config.get('username', '')}>"
        mime["To"] = ", ".join(msg.to)
        mime["Subject"] = msg.subject

        if msg.cc:
            mime["Cc"] = ", ".join(msg.cc)

        if msg.body_text:
            mime.attach(MIMEText(msg.body_text, "plain", "utf-8"))
        if msg.body_html:
            mime.attach(MIMEText(msg.body_html, "html", "utf-8"))

        return mime

    def enviar(self, msg: EmailMessage) -> EmailResult:
        """Envia un email via SMTP."""
        if not self.configurado():
            return EmailResult(
                ok=False,
                error="Email no configurado. Agregar credenciales a auth.json",
            )

        all_recipients = msg.to + msg.cc + msg.bcc

        if not all_recipients:
            return EmailResult(ok=False, error="No hay destinatarios para enviar")

        try:
            mime = self._build_mime(msg)

            host = self._config["smtp_host"]
            port = int(self._config.get("smtp_port", 587))
            username = self._config.get("username", "")
            password = self._config.get("password", "")

            context = ssl.create_default_context()

            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.sendmail(
                    username,
                    all_recipients,
                    mime.as_string(),
                )

            return EmailResult(ok=True, recipients=all_recipients)
        except Exception as e:
            return EmailResult(ok=False, error=str(e), recipients=[])

    def enviar_alerta_lead(
        self,
        cliente: str,
        mensaje: str,
        propiedad: str = "",
        canal: str = "DM Instagram",
    ) -> EmailResult:
        """Envia alerta cuando hay un lead nuevo."""
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        subject = f"Nuevo lead: {cliente} - {propiedad or 'Consulta general'}"

        text = f"""
Alerta de Lead - {now}
{"=" * 50}

Cliente: {cliente}
Canal: {canal}
Propiedad: {propiedad or "No especificada"}
Mensaje: {mensaje}

---
Estudio Inmobiliario AMBA
"""

        html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px;">
<h2 style="color: #2d5016;">Nuevo Lead</h2>
<table style="border-collapse: collapse; width: 100%;">
<tr><td style="padding: 8px; font-weight: bold;">Cliente:</td><td>{cliente}</td></tr>
<tr><td style="padding: 8px; font-weight: bold;">Canal:</td><td>{canal}</td></tr>
<tr><td style="padding: 8px; font-weight: bold;">Propiedad:</td><td>{propiedad or "No especificada"}</td></tr>
<tr><td style="padding: 8px; font-weight: bold;">Mensaje:</td><td>{mensaje}</td></tr>
</table>
<hr style="margin-top: 20px;">
<p style="color: #666; font-size: 12px;">Estudio Inmobiliario AMBA</p>
</body>
</html>
"""

        to = self._config.get("to_addresses", [])
        if not to:
            return EmailResult(ok=False, error="No hay destinatarios configurados")

        return self.enviar(EmailMessage(to=to, subject=subject, body_text=text, body_html=html))

    def enviar_reporte_semanal(
        self,
        posts_publicados: int = 0,
        leads_nuevos: int = 0,
        mejor_post: str = "",
        propiedades_activas: int = 0,
        errores: list[str] | None = None,
    ) -> EmailResult:
        """Envia reporte semanal de actividad."""
        now = datetime.now().strftime("%d/%m/%Y")
        subject = f"Reporte Semanal - {now}"

        errores_text = "\n".join(f"  - {e}" for e in (errores or [])) or "  Ninguno"

        text = f"""
Reporte Semanal - {now}
{"=" * 50}

Resumen:
  - Posts publicados: {posts_publicados}
  - Leads nuevos: {leads_nuevos}
  - Propiedades activas: {propiedades_activas}

Mejor post: {mejor_post or "N/A"}

Errores:
{errores_text}

---
Estudio Inmobiliario AMBA
"""

        html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px;">
<h2 style="color: #2d5016;">Reporte Semanal</h2>
<p style="color: #666;">{now}</p>
<table style="border-collapse: collapse; width: 100%;">
<tr><td style="padding: 8px; font-weight: bold;">Posts publicados:</td><td>{posts_publicados}</td></tr>
<tr><td style="padding: 8px; font-weight: bold;">Leads nuevos:</td><td>{leads_nuevos}</td></tr>
<tr><td style="padding: 8px; font-weight: bold;">Propiedades activas:</td><td>{propiedades_activas}</td></tr>
</table>
<h3>Mejor post</h3>
<p>{mejor_post or "N/A"}</p>
<h3>Errores</h3>
<pre>{errores_text}</pre>
<hr style="margin-top: 20px;">
<p style="color: #666; font-size: 12px;">Estudio Inmobiliario AMBA</p>
</body>
</html>
"""

        to = self._config.get("to_addresses", [])
        if not to:
            return EmailResult(ok=False, error="No hay destinatarios configurados")

        return self.enviar(EmailMessage(to=to, subject=subject, body_text=text, body_html=html))

    def enviar_alerta_error(
        self,
        modulo: str,
        error: str,
        contexto: str = "",
    ) -> EmailResult:
        """Envia alerta cuando ocurre un error critico."""
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        subject = f"ERROR en {modulo} - {now}"

        text = f"""
Error en {modulo}
{"=" * 50}

Fecha: {now}
Modulo: {modulo}
Error: {error}

Contexto:
{contexto or "N/A"}

Requiere atencion inmediata.

---
Estudio Inmobiliario AMBA
"""

        to = self._config.get("to_addresses", [])
        if not to:
            return EmailResult(ok=False, error="No hay destinatarios configurados")

        return self.enviar(EmailMessage(to=to, subject=subject, body_text=text))


if __name__ == "__main__":
    notifier = EmailNotifier()
    if notifier.configurado():
        print("Email configurado")
    else:
        print("Email NO configurado")
        print("Agregar credenciales a auth.json:")
        print('  "email": {"smtp_host": "smtp.gmail.com", ...}')
