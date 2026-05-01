"""Selectores del portal. Editar aquí si cambia el DOM del sitio."""

SELECTORS = {
    "login": {
        "user_field": "username",
        "pass_field": "password",
        "csrf_field": "csrfmiddlewaretoken",
    },
    "search_form": {
        "csrf_field": "csrfmiddlewaretoken",
        "pagina": "pagina",
        "base_url": "BASE_URL",
        "fecha": "fecha",
        "tipo_llamada": "tipo_llamada",
        "tel_cliente": "tel_cliente",
        "callid": "callid",
        "agente": "agente",
        "campana": "campana",
        "id_contacto_externo": "id_contacto_externo",
        "duracion": "duracion",
        "marcadas": "marcadas",
        "gestion": "gestion",
        "grabaciones_x_pagina": "grabaciones_x_pagina",
        "calificacion": "calificacion",
        "submit_id": "id_buscar_btn",
    },
    "results": {
        "audio_player_selector": "audio, audio source",
        "download_link_contains": [
            "/grabacion/descargar",
            "/recording/descargar",
            "/descargar",
            "/download",
        ],
        "table_selector": "table",
        "download_attr_candidates": ["data-url", "data-download", "onclick", "href"],
        "onclick_url_patterns": ["descargar(", "download(", "window.location", "open("],
        "audio_href_contains": ["wav", "mp3", "grab", "audio", "record"],
    },
}
