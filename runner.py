"""Descarga: login → buscar últimos N días → descargar → reportar → salir o repetir."""
from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, time as dtime, timedelta
from pathlib import Path
from typing import List, Optional

from config import settings
from config.timings import SHORT_MS
from core.browser import launch_browser
from core.logger import dump_debug, log
from core.share import connect_share, is_unc_path
from domain.audio_row import AudioRow
from portal.auth import ensure_logged_in
from portal.downloader import download_audio
from portal.results import paginate_and_collect
from portal.search import fill_and_search
from reports.csv_writer import write_csv
from reports.email_sender import send_report

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


def _search_one_campana(page, date_range: str, campana: str) -> List[AudioRow]:
    """Llena el formulario para una campaña y devuelve las filas únicas detectadas."""
    label = f"campaña '{campana}'" if campana else "(sin filtro de campaña)"
    log(f"\n🔎 Buscando {label}…")

    try:
        page.goto(settings.SEARCH_URL, wait_until="domcontentloaded")
        page.wait_for_selector("form#form-buscar-grabacion", timeout=SHORT_MS)
        fill_and_search(page, date_range, campana=campana)
    except Exception as e:
        log(f"❌ Error en búsqueda de {label}: {e}")
        dump_debug(page, "search_error", force=True, logs_dir=settings.LOGS_DIR)
        return []

    rows = paginate_and_collect(page)
    log(f"   🎧 Audios en {label}: {len(rows)}")
    return rows


def _already_downloaded(row: AudioRow) -> bool:
    """True si el archivo de `row` ya existe (con tamaño > 0) en DOWNLOADS_DIR.

    Acepta tanto el nombre nuevo (UID) como el viejo (completo).
    """
    candidates = []
    if row.expected_filename:
        candidates.append(row.expected_filename)
    from portal.downloader import filename_from_url
    old_name = filename_from_url(row.url)
    if old_name and old_name not in candidates:
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


def _download_all(page, rows: List[AudioRow]) -> None:
    """Descarga cada fila salteando las que ya existen. Mutates `rows[i].status`."""
    total = len(rows)
    for i, r in enumerate(rows, start=1):
        if _already_downloaded(r):
            r.status = "skipped"
            r.saved_as = r.expected_filename or ""
            continue
        try:
            target = _download_with_retries(page, r.url)
            r.status = "ok"
            r.saved_as = target.name
            log(f"   [{i}/{total}] ✓ {target.name}")
        except Exception as e:
            r.status = "failed"
            r.error = str(e)
            log(f"   [{i}/{total}] ✗ Error definitivo: {e}")


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


def _generate_report(rows: List[AudioRow]) -> Optional[Path]:
    """Escribe el reporte CSV y devuelve la ruta. Devuelve None si no hay filas."""
    if not rows:
        log("📊 No hay filas para reportar.")
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = settings.LOGS_DIR / "reportes" / f"reporte_{stamp}.csv"
    write_csv(csv_path, rows)
    log(f"📊 Reporte CSV: {csv_path}")
    return csv_path


def _send_email_report(
    csv_path: Path,
    date_range: str,
    rows: List[AudioRow],
    duration_sec: float,
) -> None:
    """Compone el cuerpo del email con un resumen y lo envía con el CSV adjunto."""
    counts = Counter(r.status for r in rows)
    by_camp: Counter[str] = Counter()
    for r in rows:
        if r.status in ("ok", "skipped"):
            by_camp[r.campana or "(sin campaña)"] += 1

    body_lines = [
        f"Reporte de descarga — {date_range}",
        f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Duración: {duration_sec:.1f} segundos",
        "",
        f"Total de audios encontrados: {len(rows)}",
        f"  Descargados:  {counts.get('ok', 0)}",
        f"  Omitidos:     {counts.get('skipped', 0)} (ya existían)",
        f"  Fallidos:     {counts.get('failed', 0)}",
        "",
    ]

    if by_camp:
        body_lines.append("Por campaña (ok + omitidos):")
        for camp, n in sorted(by_camp.items(), key=lambda kv: -kv[1]):
            body_lines.append(f"  • {camp}: {n}")
        body_lines.append("")

    body_lines.append("Detalle completo: ver el CSV adjunto.")
    body = "\n".join(body_lines)

    subject = f"[Bot Descarga] {date_range} — {counts.get('ok', 0)} ok / {counts.get('failed', 0)} fallidos"
    send_report(csv_path, subject=subject, body=body)


def _run_once() -> None:
    """Una corrida completa: login, búsqueda(s) por campaña, descarga y reporte."""
    _ensure_downloads_dir()

    start_ts = time.monotonic()
    date_range = _compute_date_range(settings.DAYS_BACK)
    log(f"📅 Rango de descarga: {date_range}")

    campanas = _parse_campanas(settings.CAMPANAS)
    if campanas:
        log(f"📋 {len(campanas)} campaña(s) a procesar: {', '.join(campanas)}")

    iter_campanas = campanas or [""]
    all_rows: List[AudioRow] = []
    seen_urls: set[str] = set()

    with launch_browser(headless=settings.HEADLESS) as page:
        try:
            log("🔐 Iniciando sesión…")
            ensure_logged_in(page)
            log("✅ Login OK")
        except Exception as e:
            log(f"❌ Error de login: {e}")
            dump_debug(page, "login_error", force=True, logs_dir=settings.LOGS_DIR)
            raise

        # Recolectar filas únicas (por URL) atravesando todas las campañas.
        for camp in iter_campanas:
            for r in _search_one_campana(page, date_range, camp):
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_rows.append(r)

        log(f"\n🎧 Total de audios únicos: {len(all_rows)}")

        # Descargar (mutates status en cada fila).
        _download_all(page, all_rows)

    # Resumen + reporte.
    duration_sec = time.monotonic() - start_ts
    counts = Counter(r.status for r in all_rows)
    log(
        f"📦 Resumen — descargados: {counts.get('ok', 0)}, "
        f"omitidos (ya existían): {counts.get('skipped', 0)}, "
        f"fallidos: {counts.get('failed', 0)} "
        f"(en {duration_sec:.1f}s)"
    )

    csv_path = _generate_report(all_rows)
    if csv_path:
        _send_email_report(csv_path, date_range, all_rows, duration_sec)


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
