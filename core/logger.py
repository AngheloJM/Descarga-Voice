"""Logging mínimo y dump de snapshots HTML+PNG ante errores."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def log(msg: str) -> None:
    """Imprime mensaje en consola con flush inmediato."""
    print(msg, flush=True)


def ts() -> str:
    """Timestamp YYYYMMDD_HHMMSS."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def dump_debug(page, tag: str = "debug", force: bool = False, logs_dir: Path = Path("logs")) -> None:
    """Guarda snapshot (HTML + PNG) de la página solo si force=True."""
    if not force:
        return
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        stamp = ts()
        html = logs_dir / f"{stamp}_{tag}.html"
        png = logs_dir / f"{stamp}_{tag}.png"
        try:
            html.write_text(page.content(), encoding="utf-8")
        except Exception:
            pass
        try:
            page.screenshot(path=str(png), full_page=True)
        except Exception:
            pass
        log(f"[DEBUG] Guardado: {html.name} / {png.name}")
    except Exception:
        pass
