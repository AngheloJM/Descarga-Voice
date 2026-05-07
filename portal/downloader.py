"""Descarga de archivos de audio mediante un click programático <a download>."""
from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Optional


def filename_from_url(url: str) -> Optional[str]:
    """Extrae el nombre original del archivo del query param `filename`.

    Ejemplo: '...?filename=/2026-04-30/Inbound-46-...-1777553950.107653.mp3'
             → 'Inbound-46-...-1777553950.107653.mp3'.
    """
    try:
        qs = urllib.parse.urlparse(url).query
        params = urllib.parse.parse_qs(qs)
        raw = params.get("filename", [""])[0]
        return Path(raw).name if raw else None
    except Exception:
        return None


def target_filename(url: str) -> Optional[str]:
    """Devuelve el nombre LOCAL bajo el cual se guarda el audio.

    Toma el último segmento tras el último '-' del nombre original (el UID
    único de la llamada en el portal) y le añade la extensión.

    Ej: 'Inbound-46-57044762-1777553950.107653.mp3' → '1777553950.107653.mp3'.

    Si el nombre no sigue ese patrón, cae al nombre original.
    """
    original = filename_from_url(url)
    if not original:
        return None
    p = Path(original)
    suffix = p.suffix or ".mp3"
    stem = p.stem
    if "-" in stem:
        uid = stem.rsplit("-", 1)[-1].strip()
        if uid:
            return f"{uid}{suffix}"
    return original


def download_audio(page, url: str, download_dir: Path) -> Path:
    """Descarga `url` y la guarda con el UID como nombre.

    Para garantizar atomicidad: primero escribe `<uid>.mp3.partial` y al
    terminar lo renombra a `<uid>.mp3`. Si la descarga se interrumpe a
    mitad, lo peor que queda es un `.partial` huérfano que el skip-check
    ignora en la siguiente corrida.
    """
    with page.expect_event("download") as dl_info:
        page.evaluate(
            """(u) => {
                const a = document.createElement('a');
                a.href = u;
                a.download = '';
                document.body.appendChild(a);
                a.click();
                a.remove();
            }""",
            url,
        )
    dl = dl_info.value

    desired = target_filename(url) or dl.suggested_filename
    final = download_dir / desired
    partial = final.with_suffix(final.suffix + ".partial")

    try:
        dl.save_as(str(partial))
        partial.replace(final)
    except Exception:
        try:
            if partial.exists():
                partial.unlink()
        except Exception:
            pass
        raise

    return final
