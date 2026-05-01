"""Descarga de archivos de audio mediante un click programático <a download>."""
from __future__ import annotations

from pathlib import Path


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
