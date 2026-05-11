"""Script de diagnóstico: prueba conexión, lectura y escritura en DOWNLOADS_DIR.

NO es un test automatizado: requiere `.env` real, credenciales y red.
Se invoca a mano para validar configuración antes de correr el bot.

Uso:
    py scripts\\diagnose_share.py

Sale con código 0 si todo OK, 1 si algo falla.
"""
from __future__ import annotations

import sys
import time
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
    # Forzamos una sesión fresca: si hay una sesión previa, se cierra primero
    # para que el test realmente valide las credenciales del .env (sin esto,
    # un cache de Windows podría hacer que el test "pase" con otras creds).
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

    # 2) Crear la carpeta si no existe
    log("\n📁 Verificando/creando carpeta…")
    try:
        dl.mkdir(parents=True, exist_ok=True)
        log(f"   ✓ Carpeta accesible: {dl}")
    except Exception as e:
        log(f"   ✗ No se puede acceder/crear: {e}")
        return 1

    # 3) Listar contenido
    log("\n📖 Listando contenido…")
    try:
        items = list(dl.iterdir())
        log(f"   ✓ OK — {len(items)} elemento(s)")
    except Exception as e:
        log(f"   ✗ Error al listar: {e}")
        return 1

    # 4) Escribir archivo de prueba
    test_file = dl / f".bot_test_{int(time.time())}.txt"
    log(f"\n✏️  Escribiendo archivo de prueba ({test_file.name})…")
    try:
        test_file.write_text("hola desde el bot\n", encoding="utf-8")
        log(f"   ✓ Escritura OK ({test_file.stat().st_size} bytes)")
    except Exception as e:
        log(f"   ✗ No se puede escribir: {e}")
        return 1

    # 5) Leer de vuelta
    log("\n📚 Leyendo el archivo de prueba…")
    try:
        content = test_file.read_text(encoding="utf-8").strip()
        if content != "hola desde el bot":
            log(f"   ⚠️ Contenido inesperado: {content!r}")
            return 1
        log("   ✓ Lectura OK (contenido coincide)")
    except Exception as e:
        log(f"   ✗ No se puede leer: {e}")
        return 1

    # 6) Borrar archivo de prueba
    log("\n🧹 Borrando archivo de prueba…")
    try:
        test_file.unlink()
        log("   ✓ Borrado OK")
    except Exception as e:
        log(f"   ⚠️ No se pudo borrar (no crítico): {e}")

    log("\n" + "=" * 60)
    log("✅ TODO OK — el bot puede leer/escribir en este destino.")
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
