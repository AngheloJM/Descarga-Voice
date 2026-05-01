"""Login en el portal."""
from __future__ import annotations

from playwright.sync_api import TimeoutError as PWTimeout

from config import settings
from config.timings import NET_IDLE_MS, SHORT_MS
from core.logger import dump_debug


def ensure_logged_in(page) -> None:
    """Garantiza que la página quede en el formulario de búsqueda autenticado."""
    page.goto(settings.LOGIN_URL, wait_until="domcontentloaded")

    if page.locator("form[role='form'] input[name='username']").count() > 0:
        page.fill("input[name='username']", settings.PORTAL_USER)
        page.fill("input[name='password']", settings.PORTAL_PASS)
        page.click("form[role='form'] button[type='submit']")
        try:
            page.wait_for_load_state("networkidle", timeout=NET_IDLE_MS)
        except Exception:
            pass

    try:
        if page.locator("a.menu-link[href='/grabacion/buscar/']").count() > 0:
            page.click("a.menu-link[href='/grabacion/buscar/']")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=SHORT_MS)
            except Exception:
                pass
    except Exception:
        pass

    page.goto(settings.SEARCH_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_selector("form#form-buscar-grabacion", timeout=SHORT_MS)
    except PWTimeout:
        dump_debug(page, "after_login_no_form", force=True, logs_dir=settings.LOGS_DIR)
        raise RuntimeError("No encuentro el formulario de búsqueda.")
