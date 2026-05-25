"""Envío del reporte por correo vía SMTP (Outlook / Office 365).

Defaults pensados para Outlook personal (smtp-mail.outlook.com:587).
Para Office 365 corporativo, usar `smtp.office365.com:587`.

Si el destinatario (`REPORT_EMAIL_TO`) está vacío, el envío no se intenta —
queda como un opt-in puro: solo si configuras correo, se envía.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from config import settings
from core.logger import log


def _is_configured() -> bool:
    return bool(
        settings.REPORT_EMAIL_TO
        and settings.REPORT_SMTP_HOST
        and settings.REPORT_SMTP_USER
        and settings.REPORT_SMTP_PASS
    )


def send_report(csv_path: Path, subject: str, body: str) -> bool:
    """Envía `csv_path` adjunto al destinatario configurado. Devuelve True si OK."""
    if not _is_configured():
        log("📧 Email no enviado: configuración incompleta en .env (revisa REPORT_*).")
        return False

    if not csv_path.exists():
        log(f"📧 Email no enviado: el CSV no existe ({csv_path}).")
        return False

    msg = EmailMessage()
    msg["From"] = settings.REPORT_EMAIL_FROM or settings.REPORT_SMTP_USER
    msg["To"] = settings.REPORT_EMAIL_TO
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        data = csv_path.read_bytes()
        msg.add_attachment(
            data,
            maintype="text",
            subtype="csv",
            filename=csv_path.name,
        )
    except Exception as e:
        log(f"📧 No pude leer el CSV para adjuntar: {e}")
        return False

    host = settings.REPORT_SMTP_HOST
    port = settings.REPORT_SMTP_PORT

    try:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(settings.REPORT_SMTP_USER, settings.REPORT_SMTP_PASS)
            s.send_message(msg)
        log(f"📧 Reporte enviado a {settings.REPORT_EMAIL_TO}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        log(f"📧 Error de autenticación SMTP: {e}")
        log("    Si usas Outlook 365 corporativo, Basic Auth puede estar deshabilitado.")
        log("    Alternativas: pedir a IT que habilite SMTP, o usar Outlook personal con App Password.")
        return False
    except Exception as e:
        log(f"📧 Error al enviar email: {e}")
        return False
