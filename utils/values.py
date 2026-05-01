"""Helpers genéricos de validación de valores."""
from __future__ import annotations


def is_empty(val) -> bool:
    """True si el valor es None o cadena vacía/whitespace."""
    if val is None:
        return True
    s = str(val).strip()
    return s == "" or s.lower() in ("nan", "none")


def is_truthy(val) -> bool:
    """Interpreta 1/true/yes/sí como True."""
    if is_empty(val):
        return False
    return str(val).strip().lower() in ("1", "true", "t", "yes", "y", "on", "si", "sí")
