"""Observador del archivo Excel: bloquea hasta detectar un cambio de mtime."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from config.timings import EXCEL_POLL_SEC
from core.logger import log


def get_mtime(path: Path) -> Optional[float]:
    """Devuelve el mtime del archivo o None si no existe."""
    try:
        return path.stat().st_mtime
    except Exception:
        return None


def wait_for_next_excel_change(
    path: Path,
    last_mtime: Optional[float] = None,
    poll_sec: float = EXCEL_POLL_SEC,
) -> float:
    """Bloquea hasta que el Excel cambie respecto a last_mtime. Devuelve el nuevo mtime."""
    log(f"⏳ Observando cambios en Excel: {path}")
    while True:
        m = get_mtime(path)
        if m is not None and (last_mtime is None or m != last_mtime):
            log("📥 Detectado cambio en el Excel.")
            return m
        time.sleep(poll_sec)
