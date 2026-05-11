"""Descarga: login → buscar últimos N días → descargar → salir o repetir cada día."""
from __future__ import annotations

import time
from datetime import datetime, time as dtime, timedelta
from pathlib import Path
from typing import Optional

from config import settings
from config.timings import SHORT_MS
from core.browser import launch_browser
from core.logger import dump_debug, log
from core.share import connect_share, is_unc_path
from portal.auth import ensure_logged_in
from portal.downloader import download_audio, filename_from_url, target_filename
from portal.results import paginate_and_collect
from portal.search import fill_and_search

DOWNLOAD_RETRIES = 2
RETRY_BACKOFF_SEC = 2


def _compute_date_range(days_back: int) -> str:
    """Rango 'dd/mm/yyyy - dd/mm/yyyy' de los últimos `days_back` días completos.

    El día de hoy queda EXCLUIDO (porque aún no terminó). Con `days_back=1`
    el rango es exactamente ayer; con `days_back=7` son los 7 días anteriores
    a hoy.
    """
    today = datetime.now().date()
    end = today - timedelta(days=1)
    start = today - timedelta(days=max(days_back, 1))
    fmt = "%d/%m/%Y"
    return f"{start.strftime(fmt)} - {end.strftime(fmt)}"


def _parse_campanas(s: str) -> list[str]:
    """Convierte 'a,b,c' en ['a','b','c'] limpiando espacios y vacíos."""
    return [c.strip() for c in (s or "").split(",") if c.strip()]


def _search_one_campana(page, date_range: str, campana: str) -> set[str]:
    """Llena el formulario para una campaña y devuelve las URLs únicas detectadas."""
    label = f"campaña '{campana}'" if campana else "(sin filtro de campaña)"
    log(f"\n🔎 Buscando {label}…")

    try:
        page.goto(settings.SEARCH_URL, wait_until="domcontentloaded")
        page.wait_for_selector("form#form-buscar-grabacion", timeout=SHORT_MS)
        fill_and_search(page, date_range, campana=campana)
    except Exception as e:
        log(f"❌ Error en búsqueda de {label}: {e}")
        dump_debug(page, "search_error", force=True, logs_dir=settings.LOGS_DIR)
        return set()

    urls = set(paginate_and_collect(page))
    log(f"   🎧 Audios en {label}: {len(urls)}")
    return urls


def _already_downloaded(url: str) -> bool:
    """True si la URL ya está descargada bajo el nombre nuevo (UID) o el viejo (completo)."""
    candidates = []
    new_name = target_filename(url)
    old_name = filename_from_url(url)
    if new_name:
        candidates.append(new_name)
    if old_name and old_name != new_name:
        candidates.append(old_name)

    for name in candidates:
        target = settings.DOWNLOADS_DIR / name
        try:
            if target.exists() and target.stat().st_size > 0:
                return True
        except Exception:
            continue
    return False


def _download_with_retries(page, url: str) -> Path:
    """Descarga `url` con reintentos en caso de error transitorio."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            return download_audio(page, url, settings.DOWNLOADS_DIR)
        except Exception as e:
            last_exc = e
            if attempt < DOWNLOAD_RETRIES:
                log(f"   ⚠️ Intento {attempt}/{DOWNLOAD_RETRIES} falló: {e} — reintentando")
                time.sleep(RETRY_BACKOFF_SEC * attempt)
    assert last_exc is not None
    raise last_exc


def _download_all(page, urls: set[str]) -> tuple[int, int, int]:
    """Descarga las URLs salteando las que ya existen. Devuelve (ok, omitidos, fallidos)."""
    ok = 0
    skipped = 0
    failed = 0
    total = len(urls)

    for i, u in enumerate(urls, start=1):
        if _already_downloaded(u):
            skipped += 1
            continue
        try:
            target = _download_with_retries(page, u)
            log(f"   [{i}/{total}] ✓ {target.name}")
            ok += 1
        except Exception as e:
            log(f"   [{i}/{total}] ✗ Error definitivo: {e}")
            failed += 1
    return ok, skipped, failed


def _ensure_downloads_dir() -> None:
    """Conecta al share si DOWNLOADS_DIR es UNC y verifica que la carpeta exista.

    No crea la carpeta — debe existir previamente. Si no existe o no es
    accesible, levanta RuntimeError con un mensaje claro.
    """
    dl = settings.DOWNLOADS_DIR
    if is_unc_path(dl) and settings.USUARIO_COMPARTIDA:
        connect_share(dl, settings.USUARIO_COMPARTIDA, settings.PASS_COMPARTIDA)

    try:
        exists = dl.exists()
    except Exception as e:
        raise RuntimeError(
            f"No se puede acceder a DOWNLOADS_DIR={dl}: {e}. "
            "Si es un share UNC, verifica USUARIO_COMPARTIDA/PASS_COMPARTIDA o conectividad de red."
        ) from e

    if not exists:
        raise RuntimeError(
            f"DOWNLOADS_DIR no existe: {dl}. "
            "Crea la carpeta manualmente en el destino antes de correr el bot."
        )


def _run_once() -> None:
    """Una corrida completa: login, búsqueda(s) por campaña y descarga deduplicada."""
    _ensure_downloads_dir()

    date_range = _compute_date_range(settings.DAYS_BACK)
    log(f"📅 Rango de descarga: {date_range}")

    campanas = _parse_campanas(settings.CAMPANAS)
    if campanas:
        log(f"📋 {len(campanas)} campaña(s) a procesar: {', '.join(campanas)}")

    # Si no hay campañas en .env, hacemos UNA búsqueda sin ese filtro.
    iter_campanas = campanas or [""]

    with launch_browser(headless=settings.HEADLESS) as page:
        try:
            log("🔐 Iniciando sesión…")
            ensure_logged_in(page)
            log("✅ Login OK")
        except Exception as e:
            log(f"❌ Error de login: {e}")
            dump_debug(page, "login_error", force=True, logs_dir=settings.LOGS_DIR)
            raise

        all_urls: set[str] = set()
        for camp in iter_campanas:
            all_urls.update(_search_one_campana(page, date_range, camp))

        log(f"\n🎧 Total de audios únicos: {len(all_urls)}")

        ok, skipped, failed = _download_all(page, all_urls)
        log(
            f"📦 Resumen — descargados: {ok}, "
            f"omitidos (ya existían): {skipped}, "
            f"fallidos: {failed}"
        )


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
