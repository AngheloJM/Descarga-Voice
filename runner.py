"""Bucle observador: detecta cambios en el Excel y procesa cada fila."""
from __future__ import annotations

import time
from pathlib import Path
from typing import List

from config import settings
from config.timings import EXCEL_POLL_SEC, SHORT_MS
from core.browser import launch_browser
from core.logger import dump_debug, log
from core.watcher import get_mtime, wait_for_next_excel_change
from domain.excel import load_rows
from domain.models import FilterRow
from portal.auth import ensure_logged_in
from portal.downloader import download_audio
from portal.results import paginate_and_collect
from portal.search import fill_and_search


def _process_row(page, row: FilterRow, idx: int, total: int) -> None:
    fecha_log = row.fecha_value or "(sin fecha)"
    log(f"\n🔎 Fila {idx}/{total} — {fecha_log}")

    page.goto(settings.SEARCH_URL, wait_until="domcontentloaded")
    page.wait_for_selector("form#form-buscar-grabacion", timeout=SHORT_MS)

    fill_and_search(page, row)

    urls = paginate_and_collect(page)
    log(f"   🎧 Audios detectados: {len(urls)}")

    ok = 0
    for u in urls:
        try:
            target = download_audio(page, u, settings.DOWNLOADS_DIR)
            log(f"      ✓ {target.name}")
            ok += 1
        except Exception as e:
            log(f"      ✗ Error al descargar: {e}")
    log(f"   📦 Descargados {ok}/{len(urls)}")


def _process_batch(page, rows: List[FilterRow]) -> None:
    try:
        page.goto(settings.SEARCH_URL, wait_until="domcontentloaded")
        page.wait_for_selector("form#form-buscar-grabacion", timeout=SHORT_MS)
    except Exception as e:
        log(f"⚠️ No se pudo abrir el formulario de búsqueda: {e}")
        dump_debug(page, "open_search_error", force=True, logs_dir=settings.LOGS_DIR)
        try:
            ensure_logged_in(page)
        except Exception as e2:
            log(f"❌ Re-login falló: {e2}")
            dump_debug(page, "relogin_error", force=True, logs_dir=settings.LOGS_DIR)
            return

    for idx, row in enumerate(rows, start=1):
        try:
            _process_row(page, row, idx, len(rows))
        except Exception as e:
            log(f"   ⚠️ Error en fila {idx}: {e}")
            dump_debug(page, f"error_row_{idx}", force=True, logs_dir=settings.LOGS_DIR)


def run() -> None:
    """Punto de entrada principal: login, observa Excel y procesa cada cambio."""
    if not settings.PORTAL_USER or not settings.PORTAL_PASS:
        raise RuntimeError("Faltan PORTAL_USER o PORTAL_PASS en .env / settings.")

    excel_path = Path(settings.DATASET_FILE)
    last_mtime = get_mtime(excel_path)

    with launch_browser(headless=True) as page:
        try:
            log("🔐 Iniciando sesión…")
            ensure_logged_in(page)
            log("✅ Login OK")
        except Exception as e:
            log(f"❌ Error de login inicial: {e}")
            dump_debug(page, "login_initial_error", force=True, logs_dir=settings.LOGS_DIR)

        while True:
            try:
                last_mtime = wait_for_next_excel_change(excel_path, last_mtime, poll_sec=EXCEL_POLL_SEC)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log(f"❌ Error observando Excel: {e}")
                time.sleep(EXCEL_POLL_SEC)
                continue

            try:
                rows = load_rows()
            except Exception as e:
                log(f"❌ No se pudo leer el Excel tras el cambio: {e}")
                dump_debug(page, "excel_read_error", force=True, logs_dir=settings.LOGS_DIR)
                continue

            _process_batch(page, rows)
