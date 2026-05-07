"""Descarga de archivos de audio mediante un click programático <a download>."""
from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Optional


def filename_from_url(url: str) -> Optional[str]:
    """Extrae el nombre del archivo del query param `filename` de la URL.

    Ejemplo: '...?filename=/2026-04-30/Inbound-46-...mp3' → 'Inbound-46-...mp3'.
    Devuelve None si no se puede determinar.
    """
    try:
        qs = urllib.parse.urlparse(url).query
        params = urllib.parse.parse_qs(qs)
        raw = params.get("filename", [""])[0]
        return Path(raw).name if raw else None
    except Exception:
        return None


def download_audio(page, url: str, download_dir: Path) -> Path:
    """Descarga `url` y devuelve la ruta donde se guardó."""
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
    target = download_dir / dl.suggested_filename
    dl.save_as(str(target))
    return target
