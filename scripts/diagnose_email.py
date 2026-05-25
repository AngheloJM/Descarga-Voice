"""Diagnóstico: envía un email de prueba con las credenciales de `.env`.

Útil para validar SMTP_HOST/PORT/USER/PASS antes de correr el bot.
NO genera CSV ni toca el portal — solo testea el envío.

Uso:
    py scripts\\diagnose_email.py
"""
from __future__ import annotations

import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Permite ejecutar el script directamente desde la raíz del repo.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config import settings  # noqa: E402
from core.logger import log  # noqa: E402
from reports.email_sender import send_report  # noqa: E402


def main() -> int:
    log("=" * 60)
    log("📧 Diagnóstico de envío de email")
    log(f"   Para:    {settings.REPORT_EMAIL_TO or '(vacío)'}")
    log(f"   Desde:   {settings.REPORT_EMAIL_FROM or settings.REPORT_SMTP_USER or '(vacío)'}")
    log(f"   SMTP:    {settings.REPORT_SMTP_HOST}:{settings.REPORT_SMTP_PORT}")
    log(f"   Usuario: {settings.REPORT_SMTP_USER or '(vacío)'}")
    log("=" * 60)

    missing = []
    if not settings.REPORT_EMAIL_TO:
        missing.append("REPORT_EMAIL_TO")
    if not settings.REPORT_SMTP_HOST:
        missing.append("REPORT_SMTP_HOST")
    if not settings.REPORT_SMTP_USER:
        missing.append("REPORT_SMTP_USER")
    if not settings.REPORT_SMTP_PASS:
        missing.append("REPORT_SMTP_PASS")
    if missing:
        log(f"❌ Faltan variables en .env: {', '.join(missing)}")
        return 1

    # Generar un CSV dummy mínimo para adjuntar.
    with tempfile.NamedTemporaryFile(
        prefix="test_email_", suffix=".csv", delete=False, mode="w", encoding="utf-8-sig"
    ) as f:
        f.write("campo;valor\nprueba;ok\n")
        tmp_csv = Path(f.name)

    try:
        log("\nEnviando email de prueba…")
        ok = send_report(
            csv_path=tmp_csv,
            subject=f"[Bot Descarga] Prueba SMTP — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            body=(
                "Este es un email de prueba enviado por scripts/diagnose_email.py.\n"
                "Si lo recibiste, las credenciales SMTP en .env funcionan correctamente.\n"
            ),
        )
    finally:
        try:
            tmp_csv.unlink()
        except Exception:
            pass

    if ok:
        log("\n" + "=" * 60)
        log("✅ Email enviado. Revisa la bandeja del destinatario.")
        log("=" * 60)
        return 0
    else:
        log("\n" + "=" * 60)
        log("❌ Fallo en el envío. Revisa el mensaje de error arriba.")
        log("=" * 60)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\n👋 Cancelado por usuario.")
        sys.exit(130)
    except Exception as e:
        log(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
