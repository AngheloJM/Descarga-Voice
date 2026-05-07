# 📥 Bot de Descarga Automatizada

Automatización en **Python + Playwright** que se conecta a un portal web, calcula un rango de fechas reciente (configurable), busca y descarga todos los archivos resultantes.

Es un proceso **one-shot**: se ejecuta una vez, descarga, y termina. Para correrlo periódicamente, prográmalo con Windows Task Scheduler (o cron en Linux/Mac).

---

## 📂 Estructura del proyecto

```
.
├── main.py                  # Entry point (CLI)
├── runner.py                # Flujo: login → buscar → descargar
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
│   └── logger.py            # log(), ts(), dump_debug()
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
│   └── values.py            # is_empty, to_str, etc.
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
DOWNLOADS_DIR=ruta/de/descargas
DAYS_BACK=1
TIMEOUT=30
SUPPRESS_TLS_WARNINGS=True
```

| Variable | Obligatorio | Descripción |
|---|---|---|
| `PORTAL_USER` | Sí | Usuario del portal |
| `PORTAL_PASS` | Sí | Contraseña del portal |
| `BASE_URL` | Sí | URL base del portal (sin slash final) |
| `DOWNLOADS_DIR` | No | Carpeta destino. Default: `./downloads` |
| `DAYS_BACK` | No | Días hacia atrás a descargar. Default: `1` (ayer → hoy) |
| `HEADLESS` | No | `true`/`false`. Default `true`. Pon `false` para ver el navegador |
| `RUN_AT` | No | `HH:MM` en hora local para correr en bucle diario. Vacío = one-shot |
| `TIMEOUT` | No | Timeout HTTP en segundos. Default: `30` |
| `LOGIN_URL` / `SEARCH_URL` / `DOWNLOAD_URL` | No | Override de paths. Default: derivados de `BASE_URL` |

### Filtros opcionales del formulario

Todos opcionales — si están vacíos, no se aplican.

| Variable | Tipo | Notas |
|---|---|---|
| `TIPO_LLAMADA` | select | Acepta nombre (`DIALER`, `INBOUND`, `MANUAL`, `PREVIEW`) o el value numérico (`1`–`4`) |
| `TEL_CLIENTE` | texto | Teléfono del cliente |
| `CALLID` | texto | Call ID exacto |
| `AGENTE` | select | Acepta el ID numérico del agente o el nombre exacto del label |
| `MARCADAS` | checkbox | `1`/`true`/`yes`/`sí` para marcar; cualquier otra cosa para desmarcar |
| `GESTION` | checkbox | Mismo formato que `MARCADAS` |
| `CAMPANAS` | lista CSV | Una o varias campañas. Acepta IDs o nombres del label, mezclados. Ej: `12,14,GT-POST-BLOQ`. El portal solo permite 1 por búsqueda, así que el bot hace **N búsquedas** y deduplica URLs |
| `GRABACIONES_X_PAGINA` | select | Cuántas grabaciones muestra por página (`10`, `25`, `50`, `100`...). **Subirlo reduce mucho la cantidad de páginas a recorrer** y hace la descarga más rápida y estable. Recomendado: `100` |

---

## 🧩 Ejemplos de uso

Cambia el comportamiento del bot editando solo el archivo `.env`. No necesitas tocar código.

### 1. Caso default — descargar todo lo de ayer
```ini
DAYS_BACK=1
# (filtros en blanco)
```
Descarga todas las llamadas del rango `ayer → hoy`, sin filtros.

### 2. Última semana, solo llamadas DIALER
```ini
DAYS_BACK=7
TIPO_LLAMADA=DIALER
```

### 3. Un agente específico (por ID o por nombre)
```ini
DAYS_BACK=1
AGENTE=550
```
o equivalentemente:
```ini
AGENTE=ALAN DIEGO CLAVIJO LAGOS
```
> El nombre debe coincidir **exacto** con el label del `<option>` en el portal (mayúsculas, espacios, acentos). Si dudas, usa el ID — más confiable.

### 4. Buscar por teléfono o Call ID puntual
```ini
DAYS_BACK=30
TEL_CLIENTE=70123456
```
o
```ini
DAYS_BACK=30
CALLID=ABC123XYZ
```

### 5. Solo llamadas con gestión registrada
```ini
DAYS_BACK=1
GESTION=1
```

### 6. Varias campañas a la vez
```ini
DAYS_BACK=1
CAMPANAS=12,14,GT-POST-BLOQ
```
El bot hace **3 búsquedas** (una por campaña), une los resultados y descarga cada audio una sola vez. Útil cuando trabajas con un grupo definido de campañas.

### 7. Combinar varios filtros
```ini
DAYS_BACK=15
TIPO_LLAMADA=INBOUND
AGENTE=550
MARCADAS=1
GESTION=1
```
Solo llamadas INBOUND, del agente 550, marcadas y con gestión, en los últimos 15 días.

### Tabla de mapeo de TIPO_LLAMADA
| Nombre | Value interno |
|---|---|
| `MANUAL` | `1` |
| `DIALER` | `2` |
| `INBOUND` | `3` |
| `PREVIEW` | `4` |

Cualquiera de los dos formatos funciona en `TIPO_LLAMADA=`.

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

El programa tiene **2 modos** según el valor de `RUN_AT`:

#### Modo one-shot (`RUN_AT` vacío)
- Calcula el rango `hoy - DAYS_BACK` → `hoy`.
- Hace login, busca con ese rango y descarga todo en `DOWNLOADS_DIR`.
- Termina cuando se completan las descargas.
- Ideal para programación externa (Windows Task Scheduler / cron).

#### Modo scheduled (`RUN_AT=HH:MM`)
- El proceso queda **corriendo indefinidamente**.
- Cada día a la hora indicada (local) ejecuta una corrida completa.
- Despierta cada 5 minutos para tolerar suspensiones de la PC.
- Detener con `Ctrl + C`.
- Ideal si quieres dejar la PC siempre encendida con el bot activo.

> Si vas a usar modo scheduled, asegúrate de que la PC no se duerma:
> `Configuración → Sistema → Inicio/apagado → Suspender = Nunca`.

---

## 🛠️ Debug

- Para ver el navegador en acción, cambia `headless=True` a `False` en [core/browser.py](core/browser.py).
- Los errores se guardan en `logs/` como:
  - HTML (`.html`)
  - Captura de pantalla (`.png`)

---

## 📦 Dependencias principales

- **Playwright** — Automatización del navegador.
- **python-dotenv** — Variables de entorno.

---

## ✨ Notas

- Si el portal cambia sus selectores, edita [config/selectors.py](config/selectors.py) o los módulos en `portal/`.
- Si necesitas ajustar timeouts/tiempos de espera, edita [config/timings.py](config/timings.py).
- Para detener una ejecución en curso: **Ctrl + C** en la terminal.
