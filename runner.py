"""Descarga one-shot: login → buscar últimos N días → descargar → salir."""
from __future__ import annotations

from datetime import datetime, timedelta

from config import settings
from config.timings import SHORT_MS
from core.browser import launch_browser
from core.logger import dump_debug, log
from portal.auth import ensure_logged_in
from portal.downloader import download_audio
from portal.results import paginate_and_collect
from portal.search import fill_and_search


def _compute_date_range(days_back: int) -> str:
    """Devuelve un rango 'dd/mm/yyyy - dd/mm/yyyy' desde hoy hasta `days_back` días atrás."""
    today = datetime.now().date()
    start = today - timedelta(days=days_back)
    fmt = "%d/%m/%Y"
    return f"{start.strftime(fmt)} - {today.strftime(fmt)}"


def run() -> None:
    if not settings.PORTAL_USER or not settings.PORTAL_PASS:
        raise RuntimeError("Faltan PORTAL_USER o PORTAL_PASS en .env / settings.")

    date_range = _compute_date_range(settings.DAYS_BACK)
    log(f"📅 Rango de descarga: {date_range}")

    with launch_browser(headless=settings.HEADLESS) as page:
        try:
            log("🔐 Iniciando sesión…")
            ensure_logged_in(page)
            log("✅ Login OK")
        except Exception as e:
            log(f"❌ Error de login: {e}")
            dump_debug(page, "login_error", force=True, logs_dir=settings.LOGS_DIR)
            raise

        try:
            page.goto(settings.SEARCH_URL, wait_until="domcontentloaded")
            page.wait_for_selector("form#form-buscar-grabacion", timeout=SHORT_MS)
            fill_and_search(page, date_range)
        except Exception as e:
            log(f"❌ Error en búsqueda: {e}")
            dump_debug(page, "search_error", force=True, logs_dir=settings.LOGS_DIR)
            raise

        urls = paginate_and_collect(page)
        log(f"🎧 Audios detectados: {len(urls)}")

        ok = 0
        for u in urls:
            try:
                target = download_audio(page, u, settings.DOWNLOADS_DIR)
                log(f"   ✓ {target.name}")
                ok += 1
            except Exception as e:
                log(f"   ✗ Error al descargar: {e}")
        log(f"📦 Descargados {ok}/{len(urls)}")
