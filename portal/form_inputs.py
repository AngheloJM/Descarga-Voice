"""Helpers para llenar inputs, selects y checkboxes del formulario de búsqueda."""
from __future__ import annotations

from config.timings import SHORT_MS
from utils.values import is_empty, is_truthy


def clear_input(page, sel: str) -> None:
    """Vacía un input usando varios fallbacks (click triple, Ctrl+A, Delete, fill('')))."""
    page.wait_for_selector(sel, timeout=SHORT_MS)
    page.locator(sel).scroll_into_view_if_needed()
    try:
        page.click(sel, click_count=3, delay=3)
    except Exception:
        pass
    try:
        page.keyboard.press("Control+A")
    except Exception:
        pass
    for key in ("Delete", "Backspace"):
        try:
            page.keyboard.press(key)
        except Exception:
            pass
    try:
        page.fill(sel, "")
    except Exception:
        pass


def set_text(page, sel: str, value: str) -> None:
    """Llena un input y dispara input/change/blur. No-op si value es vacío."""
    if is_empty(value):
        return
    try:
        clear_input(page, sel)
        page.fill(sel, str(value))
        page.evaluate(
            """(args) => {
                const {selector} = args;
                const el = document.querySelector(selector);
                if (!el) return;
                el.dispatchEvent(new Event('input',  {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                if (typeof el.blur === 'function') el.blur();
            }""",
            {"selector": sel},
        )
        try:
            page.locator(sel).evaluate("el => el.blur && el.blur()")
        except Exception:
            pass
    except Exception:
        pass


def select_option(page, sel: str, value: str) -> None:
    """Selecciona en un <select> por value y luego por label como fallback."""
    if is_empty(value):
        return
    page.wait_for_selector(sel, timeout=SHORT_MS)
    try:
        page.select_option(sel, value=value)
        return
    except Exception:
        pass
    try:
        page.select_option(sel, label=value)
    except Exception:
        pass


def set_checkbox(page, sel: str, val) -> None:
    """Marca/desmarca un checkbox según interpretación truthy del valor."""
    if is_empty(val):
        return
    page.wait_for_selector(sel, timeout=SHORT_MS)
    try:
        if is_truthy(val):
            page.check(sel, force=True)
        else:
            page.uncheck(sel)
    except Exception:
        pass
