"""Extracción de URLs de audio en la tabla de resultados (con paginación)."""
from __future__ import annotations

from typing import List, Set

from playwright.sync_api import TimeoutError as PWTimeout

from config import settings
from config.timings import NET_IDLE_MS, PAGINATE_POLL, PAGINATE_TICKS, SHORT_MS

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
    try:
        return page.eval_on_selector("#table-body", "el => el.innerText.slice(0,2000)")
    except Exception:
        return ""


def paginate_and_collect(page) -> List[str]:
    """Recolecta URLs en todas las páginas de resultados."""
    collected: Set[str] = set()

    try:
        page.wait_for_selector("#table-body", timeout=SHORT_MS)
    except PWTimeout:
        pass

    collected.update(extract_audio_urls(page))

    btns = page.locator("#pagination .page-item button")
    total_btns = btns.count()
    if total_btns <= 1:
        return list(collected)

    for i in range(1, total_btns):
        before_sig = _table_signature(page)
        try:
            btns.nth(i).click()
        except Exception:
            continue

        changed = False
        for _ in range(PAGINATE_TICKS):
            try:
                page.wait_for_timeout(PAGINATE_POLL)
            except Exception:
                pass
            after_sig = _table_signature(page)
            if after_sig and after_sig != before_sig:
                changed = True
                break
        if not changed:
            try:
                page.wait_for_load_state("networkidle", timeout=NET_IDLE_MS)
            except Exception:
                pass

        collected.update(extract_audio_urls(page))

    return list(collected)
