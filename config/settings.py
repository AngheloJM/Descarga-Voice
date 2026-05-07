from pathlib import Path
import os
from dotenv import load_dotenv

# === Paths base ===
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def _is_truthy(s: str) -> bool:
    return str(s).strip().lower() in ("1", "true", "yes", "y", "on", "si", "sí")


# === Credenciales (obligatorias) ===
PORTAL_USER = os.getenv("PORTAL_USER", "")
PORTAL_PASS = os.getenv("PORTAL_PASS", "")

# === URLs (BASE_URL es obligatorio) ===
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("Falta BASE_URL en .env")

LOGIN_URL    = os.getenv("LOGIN_URL",    f"{BASE_URL}/accounts/login/")
SEARCH_URL   = os.getenv("SEARCH_URL",   f"{BASE_URL}/grabacion/buscar/")
DOWNLOAD_URL = os.getenv("DOWNLOAD_URL", f"{BASE_URL}/grabacion/descargar/")

# === Rango de descarga ===
# Cuántos días hacia atrás buscar. Default: 1 (ayer → hoy).
DAYS_BACK = int(os.getenv("DAYS_BACK", "1"))

# === Filtros opcionales (vacío = sin filtro) ===
TIPO_LLAMADA         = os.getenv("TIPO_LLAMADA", "")
TEL_CLIENTE          = os.getenv("TEL_CLIENTE", "")
CALLID               = os.getenv("CALLID", "")
AGENTE               = os.getenv("AGENTE", "")
MARCADAS             = os.getenv("MARCADAS", "")
GESTION              = os.getenv("GESTION", "")
GRABACIONES_X_PAGINA = os.getenv("GRABACIONES_X_PAGINA", "")  # mientras más alto, menos páginas

# === Browser ===
HEADLESS = _is_truthy(os.getenv("HEADLESS", "true"))

# === Programación ===
# Si RUN_AT está vacío → one-shot (corre una vez y sale).
# Si RUN_AT="HH:MM" → bucle infinito que dispara una corrida cada día a esa hora local.
RUN_AT = os.getenv("RUN_AT", "")

# === Descargas ===
# Si DOWNLOADS_DIR está vacío o no existe en .env, cae al default `./downloads`.
_downloads_raw = os.getenv("DOWNLOADS_DIR", "").strip()
DOWNLOADS_DIR = Path(_downloads_raw) if _downloads_raw else (BASE_DIR / "downloads")

# === HTTP / TLS ===
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
SUPPRESS_TLS_WARNINGS = _is_truthy(os.getenv("SUPPRESS_TLS_WARNINGS", "true"))

# === Carpetas ===
LOGS_DIR = BASE_DIR / "logs"

for folder in (LOGS_DIR, DOWNLOADS_DIR):
    folder.mkdir(parents=True, exist_ok=True)
