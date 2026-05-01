"""Helpers genéricos para normalización de valores que vienen del Excel."""
from __future__ import annotations

import pandas as pd


def is_empty(val) -> bool:
    """True si el valor es None, vacío o NaN."""
    if val is None:
        return True
    try:
        if pd.isna(val):
            return True
    except Exception:
        pass
    s = str(val).strip()
    return s == "" or s.lower() in ("nan", "none")


def to_str(val) -> str:
    """Convierte a str si no es vacío, caso contrario devuelve ''."""
    return "" if is_empty(val) else str(val).strip()


def clean_row(d: dict) -> dict:
    """Normaliza una fila: reemplaza vacíos por None."""
    return {k: (None if is_empty(v) else v) for k, v in d.items()}


def to_int_str(val) -> str:
    """Convierte '10.0' → '10'. Si no es numérico, devuelve el str pelado."""
    s = to_str(val)
    if not s:
        return ""
    try:
        return str(int(float(s)))
    except Exception:
        return s


def is_truthy(val) -> bool:
    """Interpreta 1/true/yes/sí como True."""
    if is_empty(val):
        return False
    return str(val).strip().lower() in ("1", "true", "t", "yes", "y", "on", "si", "sí")
