"""Aplica fecha y filtros opcionales al formulario y dispara la búsqueda."""
from __future__ import annotations

from playwright.sync_api import TimeoutError as PWTimeout

from config import settings
from config.timings import SHORT_MS
from core.logger import dump_debug, log
from portal import date_picker
from portal.form_inputs import select_option, set_checkbox, set_text

# Nombre legible → value del <select id="id_tipo_llamada"> en el portal
TIPO_LLAMADA_MAP = {"DIALER": "2", "INBOUND": "3", "MANUAL": "1", "PREVIEW": "4"}


def _tipo_llamada_value(v: str) -> str:
    """Acepta 'DIALER' o '2' indistintamente y devuelve el value del select."""
    s = (v or "").strip()
    if not s or s.isdigit():
        return s
    return TIPO_LLAMADA_MAP.get(s.upper(), s)


def fill_and_search(page, date_range: str, campana: str = "") -> None:
    """Llena fecha + filtros opcionales y dispara Buscar.

    `campana` lo pasa el caller (no se lee de settings) para permitir bucles
    multi-campaña en runner.py. Acepta ID o nombre del label.
    """
    page.wait_for_selector("form#form-buscar-grabacion", timeout=SHORT_MS)

    # Fecha (siempre)
    date_picker.set_range(page, date_range)
    log(f"🗓️  Rango aplicado: {date_range}")

    # Filtros opcionales (vacío = sin filtro)
    if settings.TIPO_LLAMADA:
        select_option(page, "#id_tipo_llamada", _tipo_llamada_value(settings.TIPO_LLAMADA))
        log(f"• tipo_llamada = {settings.TIPO_LLAMADA}")
    if settings.TEL_CLIENTE:
        set_text(page, "#id_tel_cliente", settings.TEL_CLIENTE)
        log(f"• tel_cliente = {settings.TEL_CLIENTE}")
    if settings.CALLID:
        set_text(page, "#id_callid", settings.CALLID)
        log(f"• callid = {settings.CALLID}")
    if settings.AGENTE:
        select_option(page, "#id_agente", settings.AGENTE)
        log(f"• agente = {settings.AGENTE}")
    if campana:
        select_option(page, "#id_campana", campana)
        log(f"• campana = {campana}")
    if settings.MARCADAS:
        set_checkbox(page, "#id_marcadas", settings.MARCADAS)
        log(f"• marcadas = {settings.MARCADAS}")
    if settings.GESTION:
        set_checkbox(page, "#id_gestion", settings.GESTION)
        log(f"• gestion = {settings.GESTION}")
    if settings.GRABACIONES_X_PAGINA:
        select_option(page, "#id_grabaciones_x_pagina", settings.GRABACIONES_X_PAGINA)
        log(f"• grabaciones_x_pagina = {settings.GRABACIONES_X_PAGINA}")

    # Submit
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
