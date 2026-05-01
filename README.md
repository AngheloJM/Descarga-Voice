# 📥 Bot de Descarga Automatizada

Automatización en **Python + Playwright** que se conecta a un portal web, aplica filtros desde un archivo Excel y descarga los archivos resultantes.

El script queda **observando el Excel**: cada vez que guardes cambios, se ejecutará el proceso de búsqueda y descarga.

---

## 📂 Estructura del proyecto

```
.
├── main.py                  # Entry point (CLI)
├── runner.py                # Bucle observador del Excel
├── requirements.txt         # Dependencias del proyecto
├── README.md                # Documentación del proyecto
├── .env                     # Variables de entorno (ignorado en git)
│
├── config/                  # Configuración centralizada
│   ├── settings.py          # Rutas, URLs, credenciales (.env)
│   ├── timings.py           # Timeouts y tiempos de espera
│   └── selectors.py         # Selectores del DOM del portal
│
├── core/                    # Infraestructura genérica
│   ├── browser.py           # Context manager Playwright
│   ├── logger.py            # log(), ts(), dump_debug()
│   └── watcher.py           # Observador de cambios en Excel
│
├── domain/                  # Modelos y carga de datos
│   ├── models.py            # @dataclass FilterRow
│   └── excel.py             # Lectura + normalización del Excel
│
├── portal/                  # Adaptadores del sitio
│   ├── auth.py              # Login
│   ├── form_inputs.py       # Helpers set_text/select/checkbox
│   ├── date_picker.py       # DateRangePicker
│   ├── search.py            # Llenar formulario + submit
│   ├── results.py           # Extracción de URLs + paginación
│   └── downloader.py        # Descarga de archivos
│
├── utils/                   # Utilidades genéricas
│   └── values.py            # is_empty, to_str, clean_row, etc.
│
├── data/
│   └── dataset.xlsx         # Excel con filtros a aplicar
│
├── downloads/               # Archivos descargados
└── logs/                    # Errores y capturas (HTML + PNG)
```

---

## ⚙️ Instalación

1. Crear un entorno virtual:
   ```
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

2. Instalar dependencias:
   ```
   pip install -r requirements.txt
   ```

3. Instalar navegadores de Playwright (una sola vez):
   ```
   playwright install
   ```

4. Crear archivo `.env` con tus credenciales y rutas (ver sección "Variables de entorno").

---

## 🔐 Variables de entorno

Crea un archivo `.env` en la raíz con:

```
PORTAL_USER=tu_usuario
PORTAL_PASS=tu_password
BASE_URL=https://...
DATASET_FILE=ruta/al/dataset.xlsx
SHEET_NAME=NombreHoja
DOWNLOADS_DIR=ruta/de/descargas
TIMEOUT=30
SUPPRESS_TLS_WARNINGS=True
```

`BASE_URL` es **obligatorio**. Si falta, el script falla al iniciar.

---

## 📊 Excel de entrada

- Archivo: `data/dataset.xlsx` (o el que indiques en `DATASET_FILE`).
- Columnas admitidas: `fecha` / `fecha_rango`, `tipo_llamada`, `tel_cliente`, `callid`, `agente`, `campana`, `id_contacto_externo`, `duracion`, `marcadas` (1/0), `gestion` (1/0), `grabaciones_x_pagina`, `calificacion`.

El script normaliza encabezados automáticamente (`Teléfono Cliente` → `tel_cliente`).

---

## ▶️ Ejecución

1. Activar entorno virtual:
   ```
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

2. Ejecutar:
   ```
   python main.py
   ```

El programa quedará en **modo observador**:
- Espera cambios en el Excel.
- Cuando detecta un guardado, carga las filas, aplica filtros y descarga los archivos en `downloads/`.
- Si ocurre un error, genera HTML + captura en `logs/`.

---

## 🛠️ Debug

- Para ver el navegador en acción, cambia `headless=True` a `False` en `core/browser.py` o expón el flag por `.env`.
- Los errores se guardan en `logs/` como:
  - HTML (`.html`)
  - Captura de pantalla (`.png`)

---

## 📦 Dependencias principales

- Playwright — Automatización del navegador.
- Pandas — Manejo de Excel.
- OpenPyXL — Lectura de `.xlsx`.
- python-dotenv — Variables de entorno.

---

## ✨ Notas

- Si el portal cambia sus selectores, edita `config/selectors.py` o los módulos en `portal/`.
- Si necesitas ajustar timeouts/tiempos de espera, edita `config/timings.py`.
- Si el Excel está abierto mientras guardas, puede bloquearse; el script reintenta varias veces.
- Para detener el observador: **Ctrl + C** en la terminal.
