"""Script de diagnóstico: prueba la conexión al share y la existencia de DOWNLOADS_DIR.

NO es un test automatizado: requiere `.env` real, credenciales y red.
Se invoca a mano para validar configuración antes de correr el bot.

Comprueba únicamente:
  1. Conectividad/credenciales al share (si es UNC y hay credenciales).
  2. Que `DOWNLOADS_DIR` exista.

No lista contenidos ni escribe archivos en el destino.

Uso:
    py scripts\\diagnose_share.py

Sale con código 0 si todo OK, 1 si algo falla.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Permite ejecutar el script directamente desde la raíz del repo.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config import settings  # noqa: E402
from core.logger import log  # noqa: E402
from core.share import connect_share, disconnect_share, is_unc_path  # noqa: E402


def main() -> int:
    dl = settings.DOWNLOADS_DIR
    log("=" * 60)
    log(f"📂 DOWNLOADS_DIR:  {dl}")
    log(f"   Tipo de ruta:  {'UNC (red)' if is_unc_path(dl) else 'local'}")
    log(f"   Usuario share: {settings.USUARIO_COMPARTIDA or '(vacío)'}")
    log("=" * 60)

    # 1) Conectar al share si aplica.
    # Forzamos una sesión fresca para validar realmente las credenciales del .env.
    if is_unc_path(dl) and settings.USUARIO_COMPARTIDA:
        log("\n🔓 Cerrando sesiones previas (para probar credenciales limpias)…")
        disconnect_share(dl)

        log(f"\n🔐 Conectando al share con usuario '{settings.USUARIO_COMPARTIDA}'…")
        if not connect_share(dl, settings.USUARIO_COMPARTIDA, settings.PASS_COMPARTIDA):
            log("❌ No se pudo conectar al share. Verifica USUARIO_COMPARTIDA / PASS_COMPARTIDA.")
            return 1
    elif is_unc_path(dl):
        log("\nℹ️  Es UNC pero USUARIO_COMPARTIDA está vacío.")
        log("   Se asume que Windows ya tiene credenciales guardadas (cmdkey).")

    # 2) Verificar que la carpeta exista (NO la creamos)
    log("\n📁 Verificando que la carpeta exista…")
    try:
        if not dl.exists():
            log(f"   ✗ La carpeta no existe: {dl}")
            log("     Créala manualmente en el destino antes de correr el bot.")
            return 1
        log(f"   ✓ Carpeta accesible: {dl}")
    except Exception as e:
        log(f"   ✗ No se puede acceder: {e}")
        return 1

    log("\n" + "=" * 60)
    log("✅ Conexión OK y carpeta destino disponible.")
    log("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\n👋 Cancelado por usuario.")
        sys.exit(130)
    except Exception as e:
        log(f"\n❌ Error inesperado: {e}")
        sys.exit(1)
