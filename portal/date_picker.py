"""Lógica del DateRangePicker (jQuery plugin) del portal."""
from __future__ import annotations

from datetime import datetime

from config.timings import PICKER_MS
from portal.form_inputs import set_text
from utils.values import is_empty

DATE_FIELD_SEL = "#id_fecha"


def _parse_range(s: str) -> tuple[str, str]:
    s = (s or "").strip()
    if " - " in s:
        a, b = [p.strip() for p in s.split(" - ", 1)]
    else:
        a = b = s
    fmt = "%d/%m/%Y"
    ini = datetime.strptime(a, fmt).strftime(fmt)
    fin = datetime.strptime(b, fmt).strftime(fmt)
    return ini, fin


def _norm(s: str) -> str:
    s = (s or "").strip().replace("-", "/").replace(".", "/")
    if " - " in s:
        a, b = [p.strip() for p in s.split(" - ", 1)]
    else:
        a = b = s

    def z(d: str) -> str:
        parts = d.split("/")
        if len(parts) == 3:
            dd, mm, yyyy = parts
            return f"{int(dd):02d}/{int(mm):02d}/{yyyy}"
        return d

    return f"{z(a)} - {z(b)}"


def is_open(page) -> bool:
    try:
        loc = page.locator(".daterangepicker")
        return loc.count() > 0 and loc.first.is_visible()
    except Exception:
        return False


def close_overlay(page, timeout_ms: int = PICKER_MS) -> None:
    if not is_open(page):
        return
    try:
        btn = page.locator(".daterangepicker .applyBtn")
        if btn.count() > 0 and btn.first.is_visible():
            btn.first.click()
    except Exception:
        pass
    try:
        page.wait_for_selector(".daterangepicker", state="hidden", timeout=timeout_ms)
    except Exception:
        pass


def _try_plugin_api(page, ini: str, fin: str) -> bool:
    """Intenta usar la API JS del daterangepicker. Devuelve True si funcionó."""
    try:
        return bool(page.evaluate(
            """
            ({ini, fin}) => {
              const el = document.querySelector('#id_fecha');
              if (!el) return false;
              const drp = (window.$ && window.$(el).data && window.$(el).data('daterangepicker')) || null;
              if (drp && drp.setStartDate && drp.setEndDate) {
                drp.setStartDate(ini);
                drp.setEndDate(fin);
                if (drp.clickApply) drp.clickApply();
                if (drp.hide) drp.hide();
                el.dispatchEvent(new Event('input',  {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
                if (typeof el.blur === 'function') el.blur();
                return true;
              }
              return false;
            }
            """,
            {"ini": ini, "fin": fin},
        ))
    except Exception:
        return False


def _force_value(page, expected: str) -> None:
    page.evaluate(
        """
        (v) => {
          const el = document.querySelector('#id_fecha');
          if (!el) return;
          el.value = v;
          el.dispatchEvent(new Event('input',  {bubbles:true}));
          el.dispatchEvent(new Event('change', {bubbles:true}));
          el.blur && el.blur();
        }
        """,
        expected,
    )


def _read_value(page) -> str:
    try:
        return page.eval_on_selector(DATE_FIELD_SEL, "el => el.value") or ""
    except Exception:
        return ""


def set_range(page, date_range: str) -> None:
    """Setea el rango de fechas en el picker. Acepta 'dd/mm/yyyy' o 'dd/mm/yyyy - dd/mm/yyyy'."""
    if is_empty(date_range):
        return

    ini, fin = _parse_range(date_range)
    expected = f"{ini} - {fin}"

    # 1) API del plugin
    if _try_plugin_api(page, ini, fin):
        try:
            page.wait_for_timeout(120)
        except Exception:
            pass
        if _norm(_read_value(page)) != _norm(expected):
            _force_value(page, expected)
        return

    # 2) Fast path: input editable
    try:
        readonly = bool(page.eval_on_selector(DATE_FIELD_SEL, "el => !!el && !!el.readOnly"))
    except Exception:
        readonly = False

    if not readonly:
        try:
            page.fill(DATE_FIELD_SEL, expected)
            _force_value(page, expected)
            if _norm(_read_value(page)) == _norm(expected):
                return
        except Exception:
            pass

    # 3) Fallback: abrir picker y rellenar start/end
    try:
        page.click(DATE_FIELD_SEL, force=True)
        page.wait_for_selector(".daterangepicker", timeout=PICKER_MS)
    except Exception:
        _force_value(page, expected)
        return

    start_candidates = [
        ".daterangepicker input[name='daterangepicker_start']",
        ".daterangepicker .drp-inputs input[name='start']",
        ".daterangepicker .drp-inputs input:first-of-type",
    ]
    end_candidates = [
        ".daterangepicker input[name='daterangepicker_end']",
        ".daterangepicker .drp-inputs input[name='end']",
        ".daterangepicker .drp-inputs input:last-of-type",
    ]
    start_sel = next((s for s in start_candidates if page.locator(s).count() > 0), None)
    end_sel = next((s for s in end_candidates if page.locator(s).count() > 0), None)

    if start_sel and end_sel:
        set_text(page, start_sel, ini)
        set_text(page, end_sel, fin)
        try:
            page.locator(".daterangepicker .applyBtn").first.click()
        except Exception:
            pass
        try:
            page.wait_for_selector(".daterangepicker", state="hidden", timeout=2000)
        except Exception:
            pass
    else:
        set_text(page, DATE_FIELD_SEL, expected)
        try:
            page.keyboard.press("Enter")
        except Exception:
            pass

    if _norm(_read_value(page)) != _norm(expected):
        _force_value(page, expected)

    try:
        page.wait_for_timeout(120)
    except Exception:
        pass
