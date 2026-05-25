"""Modelo tipado de una fila de la tabla de resultados del portal."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from portal.downloader import filename_from_url, target_filename


@dataclass
class AudioRow:
    """Una grabación encontrada en la tabla de resultados del portal.

    Los campos hasta `username` se llenan al hacer scraping. Los campos al final
    se llenan durante el ciclo de descarga.
    """

    # Datos del portal
    url: str = ""
    fecha: str = ""
    tipo: str = ""
    tel_cliente: str = ""
    agente: str = ""
    campana: str = ""
    username: str = ""

    # Resultado de la descarga (se llena después)
    status: str = "pending"   # "ok" | "skipped" | "failed"
    saved_as: str = ""        # nombre local del archivo si se descargó
    error: str = ""           # mensaje si falló

    @property
    def uid(self) -> str:
        """UID de la llamada: último segmento del nombre original tras el último '-'."""
        original = filename_from_url(self.url) or ""
        if "-" not in original:
            from pathlib import Path
            return Path(original).stem
        from pathlib import Path
        stem = Path(original).stem
        return stem.rsplit("-", 1)[-1]

    @property
    def expected_filename(self) -> Optional[str]:
        """Nombre local bajo el cual el bot guarda este audio (UID + extensión)."""
        return target_filename(self.url)
