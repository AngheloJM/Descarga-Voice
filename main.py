"""Entry point del scraper."""
from __future__ import annotations

from core.logger import log
from runner import run


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        log("👋 Salida por teclado (Ctrl+C).")
    except Exception as e:
        log(f"❌ Error: {e}")
