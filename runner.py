"""Descarga: login → buscar últimos N días → descargar → salir o repetir cada día."""
from __future__ import annotations

import time
from datetime import datetime, time as dtime, timedelta
from typing import Optional

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


def _run_once() -> None:
    """Una corrida completa: login, búsqueda y descarga."""
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


def _parse_run_at(s: str) -> Optional[dtime]:
    """Parsea 'HH:MM' a un objeto time. Devuelve None si la cadena está vacía."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        hh_str, mm_str = s.split(":")
        return dtime(int(hh_str), int(mm_str))
    except Exception as e:
        raise RuntimeError(f"RUN_AT inválido: {s!r} (formato esperado HH:MM, ej. 03:00)") from e


def _next_run(target: dtime) -> datetime:
    """Devuelve el próximo datetime futuro que coincide con la hora `target`."""
    now = datetime.now()
    candidate = datetime.combine(now.date(), target)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _wait_until(when: datetime) -> None:
    """Espera hasta `when` despertando cada 5 min para tolerar suspensiones de la PC."""
    while True:
        remaining = (when - datetime.now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 300))


def run() -> None:
    if not settings.PORTAL_USER or not settings.PORTAL_PASS:
        raise RuntimeError("Faltan PORTAL_USER o PORTAL_PASS en .env / settings.")

    target = _parse_run_at(settings.RUN_AT)

    # One-shot: una corrida y sale (útil para Windows Task Scheduler / cron)
    if target is None:
        log("🔁 Modo: one-shot")
        _run_once()
        return

    # Scheduled: bucle infinito, una corrida diaria a la hora indicada
    log(f"⏰ Modo: scheduled — diario a las {target.strftime('%H:%M')} (hora local)")
    log("    Para detener: Ctrl + C")
    while True:
        next_at = _next_run(target)
        log(f"💤 Próxima corrida: {next_at.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            _wait_until(next_at)
        except KeyboardInterrupt:
            log("👋 Salida por teclado.")
            return

        log(f"▶️  Iniciando corrida programada — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            _run_once()
        except KeyboardInterrupt:
            log("👋 Salida por teclado durante corrida.")
            return
        except Exception as e:
            log(f"❌ Error en la corrida: {e} (continúa al día siguiente)")
