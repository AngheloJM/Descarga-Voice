"""Extracción de URLs de audio en la tabla de resultados (con paginación robusta)."""
from __future__ import annotations

from typing import List, Set

from playwright.sync_api import TimeoutError as PWTimeout

from config import settings
from config.timings import PAGINATE_TIMEOUT_MS, SHORT_MS
from core.logger import log

AUDIO_HREF_FILTER = "/api/v1/grabacion/archivo/?filename="


def _abs_url(ref: str) -> str:
    return ref if ref.startswith("http") else f"{settings.BASE_URL}{ref}"


def extract_audio_urls(page) -> List[str]:
    """Recoge las URLs de audio visibles en la tabla actual."""
    urls: Set[str] = set()

    anchors = page.locator(f"#table-body a[href*='{AUDIO_HREF_FILTER}']")
    try:
        for i in range(anchors.count()):
            href = anchors.nth(i).get_attribute("href") or ""
            if href:
                urls.add(_abs_url(href))
    except Exception:
        pass

    sources = page.locator(f"#table-body source[src*='{AUDIO_HREF_FILTER}']")
    try:
        for i in range(sources.count()):
            src = sources.nth(i).get_attribute("src") or ""
            if src:
                urls.add(_abs_url(src))
    except Exception:
        pass

    return list(urls)


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


def paginate_and_collect(page) -> List[str]:
    """Recorre todas las páginas con el botón Siguiente y acumula URLs únicas."""
    collected: Set[str] = set()

    try:
        page.wait_for_selector("#table-body", timeout=SHORT_MS)
    except PWTimeout:
        return list(collected)

    total = _detect_total_pages(page)
    log(f"   📄 {total} página(s) detectada(s)")

    page_num = 1
    collected.update(extract_audio_urls(page))
    log(f"   • Página {page_num}/{total}: {len(collected)} URLs únicas")

    while True:
        before_sig = _table_signature(page)
        if not _click_next(page):
            break

        if not _wait_for_table_change(page, before_sig):
            log("   ⚠️ La tabla no cambió tras Siguiente — abortando paginación")
            break

        page_num += 1
        collected.update(extract_audio_urls(page))
        log(f"   • Página {page_num}/{total}: {len(collected)} URLs únicas")

    return list(collected)
