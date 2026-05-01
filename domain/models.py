"""Modelo tipado para una fila de filtros del Excel."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Optional

from utils.values import is_empty


@dataclass
class FilterRow:
    """Una fila del Excel ya normalizada. Cada campo mapea 1:1 a un input del formulario."""

    fecha: Optional[str] = None
    fecha_rango: Optional[str] = None
    tipo_llamada: Optional[str] = None
    tel_cliente: Optional[str] = None
    callid: Optional[str] = None
    agente: Optional[str] = None
    campana: Optional[str] = None
    id_contacto_externo: Optional[str] = None
    duracion: Optional[str] = None
    marcadas: Optional[str] = None
    gestion: Optional[str] = None
    grabaciones_x_pagina: Optional[str] = None
    calificacion: Optional[str] = None

    @property
    def fecha_value(self) -> str:
        """Acepta `fecha` o `fecha_rango` indistintamente."""
        return self.fecha or self.fecha_rango or ""

    @classmethod
    def from_dict(cls, d: dict) -> "FilterRow":
        known = {f.name for f in fields(cls)}
        clean = {k: (None if is_empty(v) else str(v).strip()) for k, v in d.items() if k in known}
        return cls(**clean)
