"""Escritura del reporte CSV con el detalle de cada audio."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from domain.audio_row import AudioRow

CSV_HEADERS = [
    "uid",
    "fecha",
    "tipo",
    "tel_cliente",
    "agente",
    "campana",
    "username",
    "estado",          # ok | omitido | fallido | pendiente
    "archivo_local",
    "error",
    "url",
]

_STATUS_LABEL = {
    "ok": "ok",
    "skipped": "omitido",
    "failed": "fallido",
    "pending": "pendiente",
}


def write_csv(path: Path, rows: Iterable[AudioRow]) -> int:
    """Escribe las filas como CSV (UTF-8 con BOM para que Excel abra acentos OK)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CSV_HEADERS)
        for r in rows:
            writer.writerow([
                r.uid,
                r.fecha,
                r.tipo,
                r.tel_cliente,
                r.agente,
                r.campana,
                r.username,
                _STATUS_LABEL.get(r.status, r.status),
                r.saved_as,
                r.error,
                r.url,
            ])
            count += 1
    return count
