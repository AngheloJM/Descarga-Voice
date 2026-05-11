"""Conexión a recursos compartidos UNC (Windows) vía `net use`.

Permite que el bot se autentique automáticamente contra un share remoto
cuando `DOWNLOADS_DIR` es una ruta `\\\\server\\share\\...`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from core.logger import log


def is_unc_path(path) -> bool:
    """True si la ruta es UNC (`\\\\server\\share\\...`)."""
    s = str(path)
    return s.startswith("\\\\") or s.startswith("//")


def _share_root(path) -> Optional[str]:
    """De `\\\\server\\share\\sub` devuelve `\\\\server\\share`. None si no es UNC."""
    p = Path(path)
    if not is_unc_path(p):
        return None
    # parts[0] suele ser '\\server\share\' (con slash final)
    root = p.parts[0].rstrip("\\/")
    return root or None


def connect_share(path, user: str, password: str) -> bool:
    """Establece una sesión `net use` contra el share del `path`.

    Devuelve True si la conexión quedó establecida (o ya existía).
    """
    root = _share_root(path)
    if not root:
        return False

    try:
        result = subprocess.run(
            ["net", "use", root, password, f"/user:{user}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as e:
        log(f"⚠️ No pude ejecutar 'net use' para {root}: {e}")
        return False

    if result.returncode == 0:
        log(f"🔗 Share conectado: {root}")
        return True

    err = (result.stderr or result.stdout or "").strip().lower()
    # "1219" = ya conectado con otras credenciales; tratamos como éxito porque
    # significa que sí hay sesión activa contra ese servidor.
    if "1219" in err or "already connected" in err or "ya hay una conexión" in err:
        log(f"🔗 Share ya estaba conectado: {root}")
        return True

    log(f"⚠️ 'net use' devolvió código {result.returncode} para {root}: {err}")
    return False
