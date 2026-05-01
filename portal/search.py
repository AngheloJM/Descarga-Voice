"""Aplica los filtros de una `FilterRow` al formulario y dispara la búsqueda."""
from __future__ import annotations

from playwright.sync_api import TimeoutError as PWTimeout

from config import settings
from config.timings import SHORT_MS
from core.logger import dump_debug, log
from domain.models import FilterRow
from portal import date_picker
from portal.form_inputs import select_option, set_checkbox, set_text
from utils.values import is_empty, to_int_str, to_str

# Mapeo de nombres legibles → value del <select> tipo_llamada
TIPO_LLAMADA_MAP = {"DIALER": "2", "INBOUND": "3", "MANUAL": "1", "PREVIEW": "4"}


def _map_tipo_llamada(v: str | None) -> str:
    s = to_str(v)
    if not s:
        return ""
    try:
        return str(int(float(s)))  # "3.0" -> "3"
    except Exception:
        return TIPO_LLAMADA_MAP.get(s.upper(), "")


def _safe(action, label: str) -> None:
    """Ejecuta un setter de campo con captura silenciosa y log de éxito."""
    try:
        action()
        log(f"• {label} ✓")
    except Exception:
        pass


def fill_and_search(page, row: FilterRow) -> None:
    """Llena el formulario con `row` y hace clic en Buscar."""
    page.wait_for_selector("form#form-buscar-grabacion", timeout=SHORT_MS)

    # 1) Fecha (campo principal del flujo)
    date_picker.set_range(page, row.fecha_value)
    log("🗓️  Fechas OK")

    # 2) Resto de filtros (todos opcionales)
    _safe(lambda: select_option(page, "#id_tipo_llamada", _map_tipo_llamada(row.tipo_llamada)), "tipo_llamada")
    _safe(lambda: set_text(page, "#id_tel_cliente", to_str(row.tel_cliente)), "tel_cliente")
    _safe(lambda: set_text(page, "#id_callid", to_str(row.callid)), "callid")
    _safe(lambda: select_option(page, "#id_agente", to_str(row.agente)), "agente")
    _safe(lambda: select_option(page, "#id_campana", to_str(row.campana)), "campana")
    _safe(lambda: set_text(page, "#id_id_contacto_externo", to_str(row.id_contacto_externo)), "id_contacto_externo")

    if not is_empty(row.duracion):
        _safe(lambda: set_text(page, "#id_duracion", to_int_str(row.duracion)), "duracion")

    _safe(lambda: set_checkbox(page, "#id_marcadas", row.marcadas), "marcadas")
    _safe(lambda: set_checkbox(page, "#id_gestion", row.gestion), "gestion")

    if not is_empty(row.grabaciones_x_pagina):
        _safe(lambda: select_option(page, "#id_grabaciones_x_pagina", to_int_str(row.grabaciones_x_pagina)), "grabaciones_x_pagina")

    _safe(lambda: select_option(page, "#id_calificacion", to_str(row.calificacion)), "calificacion")

    # 3) Submit
    try:
        if page.locator("#id_buscar_btn").count() > 0:
            page.click("#id_buscar_btn")
        else:
            page.get_by_role("button", name="Buscar").click()
    finally:
        try:
            page.wait_for_selector("#table-body tr", timeout=SHORT_MS)
        except PWTimeout:
            dump_debug(page, "no_rows_after_search", force=True, logs_dir=settings.LOGS_DIR)
