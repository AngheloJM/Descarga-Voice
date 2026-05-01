"""Carga y normalización del Excel de filtros."""
from __future__ import annotations

import time
from pathlib import Path
from typing import List

import pandas as pd

from config import settings
from config.timings import EXCEL_READ_BACKOFF_SEC, EXCEL_READ_RETRIES
from core.logger import log
from domain.models import FilterRow

# Aliases comunes -> nombres esperados por el form
COLUMN_ALIASES = {
    "id_contacto": "id_contacto_externo",
    "id_contacto_ext": "id_contacto_externo",
    "telefono": "tel_cliente",
    "telefono_cliente": "tel_cliente",
    "grabaciones": "grabaciones_x_pagina",
    "grabaciones_por_pagina": "grabaciones_x_pagina",
    "tipo_llamad": "tipo_llamada",
}


def _norm_header(c: str) -> str:
    return str(c).strip().lower().replace(" ", "_")


def _read_excel_with_retry(path: Path, sheet: str) -> pd.DataFrame:
    last_err: Exception | None = None
    for _ in range(EXCEL_READ_RETRIES):
        try:
            return pd.read_excel(
                path,
                sheet_name=sheet,
                engine="openpyxl",
                dtype=str,
                keep_default_na=True,
            )
        except Exception as e:
            last_err = e
            time.sleep(EXCEL_READ_BACKOFF_SEC)
    raise RuntimeError(f"No se pudo leer el Excel: {path} — {last_err}")


def load_rows() -> List[FilterRow]:
    """Lee `settings.DATASET_FILE` y devuelve filas tipadas."""
    path = Path(settings.DATASET_FILE)
    if not path.exists():
        raise RuntimeError(f"No existe el Excel: {path}")

    df = _read_excel_with_retry(path, settings.SHEET_NAME)
    if df.empty:
        raise RuntimeError("El Excel no tiene filas.")

    df.columns = [_norm_header(c) for c in df.columns]
    df.rename(columns=COLUMN_ALIASES, inplace=True)

    rows = [FilterRow.from_dict(r.to_dict()) for _, r in df.iterrows()]

    log("📄 Encabezados: " + ", ".join(df.columns))
    log(f"📘 Filas a procesar: {len(rows)}")
    return rows
