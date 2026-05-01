"""Context manager para el navegador Playwright."""
from __future__ import annotations

from contextlib import contextmanager

from playwright.sync_api import sync_playwright


@contextmanager
def launch_browser(headless: bool = True, accept_downloads: bool = True):
    """Lanza Chromium, crea contexto + página y limpia al salir.

    Yields:
        page: la Page lista para usar.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(accept_downloads=accept_downloads)
        page = context.new_page()
        try:
            yield page
        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
