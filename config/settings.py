from pathlib import Path
import os
from dotenv import load_dotenv

# === Paths base ===
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

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

# === Dataset ===
DATASET_FILE = Path(os.getenv("DATASET_FILE", BASE_DIR / "data" / "dataset.xlsx"))
SHEET_NAME   = os.getenv("SHEET_NAME", "Sheet1")

# === Descargas ===
DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", BASE_DIR / "downloads"))

# === HTTP / TLS ===
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
SUPPRESS_TLS_WARNINGS = str(os.getenv("SUPPRESS_TLS_WARNINGS", "true")).strip().lower() in (
    "1", "true", "yes", "y"
)

# === Carpetas ===
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

for folder in (LOGS_DIR, DOWNLOADS_DIR, DATA_DIR):
    folder.mkdir(parents=True, exist_ok=True)
