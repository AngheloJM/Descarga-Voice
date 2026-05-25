"""Extracción de filas de la tabla de resultados (con paginación robusta)."""
from __future__ import annotations

from typing import List

from playwright.sync_api import TimeoutError as PWTimeout

from config import settings
from config.timings import PAGINATE_TIMEOUT_MS, SHORT_MS
from core.logger import log
from domain.audio_row import AudioRow

AUDIO_HREF_FILTER = "/api/v1/grabacion/archivo/?filename="


def _abs_url(ref: str) -> str:
    return ref if ref.startswith("http") else f"{settings.BASE_URL}{ref}"


def extract_audio_rows(page) -> List[AudioRow]:
    """Recoge filas completas (con metadatos) de la tabla actual."""
    raw = page.evaluate(
        """
        () => {
            const rows = document.querySelectorAll('#table-body tr');
            const out = [];
            for (const row of rows) {
                const tds = row.querySelectorAll('td');
                if (tds.length < 8) continue;

                // URL: priorizar <source>, fallback al <a>
                let url = '';
                const source = row.querySelector('source[src*="/api/v1/grabacion/archivo"]');
                if (source) url = source.getAttribute('src') || '';
                if (!url) {
                    const link = row.querySelector('a[href*="/api/v1/grabacion/archivo"]');
                    if (link) url = link.getAttribute('href') || '';
                }
                if (!url) continue;

                const txt = (i) => ((tds[i] && tds[i].innerText) || '').trim();
                out.push({
                    url: url,
                    fecha:       txt(2),
                    tipo:        txt(3),
                    tel_cliente: txt(4),
                    agente:      txt(5),
                    campana:     txt(6),
                    username:    txt(10),
                });
            }
            return out;
        }
        """
    )

    rows: List[AudioRow] = []
    for r in raw or []:
        rows.append(
            AudioRow(
                url=_abs_url(r.get("url", "")),
                fecha=r.get("fecha", ""),
                tipo=r.get("tipo", ""),
                tel_cliente=r.get("tel_cliente", ""),
                agente=r.get("agente", ""),
                campana=r.get("campana", ""),
                username=r.get("username", ""),
            )
        )
    return rows


def _table_signature(page) -> str:
    """Snapshot del contenido de la tabla para detectar cambios entre páginas."""
    try:
        return page.eval_on_selector("#table-body", "el => el.innerText.slice(0,2000)")
    except Exception:
        return ""


def _detect_total_pages(page) -> int:
    """Lee el paginador y devuelve la última página (1 si no hay paginación)."""
    try:
        return int(page.evaluate(
            """() => {
                let max = 1;
                for (const b of document.querySelectorAll('#pagination button[data-page]')) {
                    const n = parseInt(b.getAttribute('data-page') || '0', 10);
                    if (n > max) max = n;
                }
                const active = document.querySelector('#pagination li.active button');
                if (active) {
                    const n = parseInt((active.textContent || '').trim(), 10);
                    if (Number.isFinite(n) && n > max) max = n;
                }
                return max;
            }"""
        ))
    except Exception:
        return 1


def _wait_for_table_change(page, before_sig: str) -> bool:
    """Espera a que el contenido de la tabla cambie. True si cambió, False si timeout."""
    try:
        page.wait_for_function(
            """(prev) => {
                const el = document.querySelector('#table-body');
                if (!el) return false;
                return el.innerText.slice(0, 2000) !== prev;
            }""",
            arg=before_sig,
            timeout=PAGINATE_TIMEOUT_MS,
        )
        return True
    except PWTimeout:
        return False


def _click_next(page) -> bool:
    """Hace click en 'Siguiente' si está habilitado. Devuelve False si no hay siguiente."""
    next_btn = page.locator(
        "#pagination li.page-item:not(.disabled) button:has-text('Siguiente')"
    )
    if next_btn.count() == 0:
        return False
    try:
        next_btn.first.scroll_into_view_if_needed()
        next_btn.first.click()
        return True
    except Exception as e:
        log(f"   ⚠️ Error al hacer click en Siguiente: {e}")
        return False


def paginate_and_collect(page) -> List[AudioRow]:
    """Recorre todas las páginas con 'Siguiente' y acumula filas únicas por URL."""
    seen_urls: set[str] = set()
    collected: List[AudioRow] = []

    def add(rows: List[AudioRow]) -> None:
        for r in rows:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                collected.append(r)

    try:
        page.wait_for_selector("#table-body", timeout=SHORT_MS)
    except PWTimeout:
        return collected

    total = _detect_total_pages(page)
    log(f"   📄 {total} página(s) detectada(s)")

    page_num = 1
    add(extract_audio_rows(page))
    log(f"   • Página {page_num}/{total}: {len(collected)} filas únicas")

    while True:
        before_sig = _table_signature(page)
        if not _click_next(page):
            break

        if not _wait_for_table_change(page, before_sig):
            log("   ⚠️ La tabla no cambió tras Siguiente — abortando paginación")
            break

        page_num += 1
        add(extract_audio_rows(page))
        log(f"   • Página {page_num}/{total}: {len(collected)} filas únicas")

    return collected
