# 🤖 MT5 Backtest Pro — Automatización de backtests masivos en MetaTrader 5

App de escritorio para **correr backtests en lote** sobre Expert Advisors de MetaTrader 5 sin intervención manual. Detecta automáticamente la instalación de MT5, lanza cada `.ex5` con su configuración, guarda los reportes y notifica por Telegram al terminar.

---

## ✨ Features

- 🔍 **Auto-detección de MT5** — Encuentra automáticamente el ejecutable y la carpeta de datos sin configuración manual
- ⚙️ **Panel de configuración integrado** — Rutas de MT5 y Telegram, todo desde la app
- 📂 **Selección de carpeta de EAs** — Explorador de carpetas con botón de refresco en tiempo real
- 📊 **Batch backtesting** — Lanza todos los `.ex5` de una carpeta en secuencia automáticamente
- 📅 **Rango de fechas configurable** — Date pickers visuales con opción de rango por defecto
- 💱 **Símbolo y timeframe** — Combos con los activos e intervalos más comunes
- 📁 **Carpeta de informes configurable** — Elige dónde se guardan los `.html` generados
- 📨 **Notificaciones Telegram** — Mensaje automático al iniciar y al terminar el backtest con resumen
- 🟢 **Activity Log** — Log en tiempo real con timestamps de cada operación
- 🚫 **Banner de configuración** — Aviso claro si MT5 no está configurado antes de correr
- 🎛️ **Ajustes Avanzados** — Modelado (ticks reales / OHLC / precio de apertura), apalancamiento, delay de ejecución y modo visual, todo configurable sin tocar código
- ⏹️ **Botón Detener** — Cancela el backtest en curso (termina el EA actual y no continúa con los siguientes)
- 📦 **Ejecutable standalone** — `.exe` listo para usar, sin instalar Python ni dependencias

---

## 🛠️ Stack / Tecnologías

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.x-1f6aa5?style=flat-square&logo=python&logoColor=white)
![PyInstaller](https://img.shields.io/badge/PyInstaller-6.x-2c2c2c?style=flat-square&logo=python&logoColor=white)
![MetaTrader 5](https://img.shields.io/badge/MetaTrader_5-compatible-00d9ff?style=flat-square)
![Telegram](https://img.shields.io/badge/Telegram_Bot_API-integrated-26A5E4?style=flat-square&logo=telegram&logoColor=white)

---

## 🚀 Descarga rápida

**No necesitas Python.** Descarga el `.exe` directamente y ejecuta:

👉 [**Descargar MT5_Backtest_Pro.exe** (v1.2)](https://github.com/rovamad/automata-mt5/releases/download/v1.2/MT5_Backtest_Pro.exe)

1. Descarga el `.exe` del enlace de arriba
2. Colócalo en cualquier carpeta (ej. `C:\Automata\`)
3. Ejecuta — al abrirse por primera vez aparece el banner de configuración
4. Abre **⚙ Configuración** y completa las rutas de MT5 (se autodetectan)
5. Configura símbolo, timeframe, fechas y pulsa **Start Backtest**

---

## ⚙️ Configuración

Al abrir por primera vez, la app muestra un banner rojo indicando que MT5 no está configurado. Pulsa **⚙ Configuración** para abrir el panel:

### Pestaña MT5

| Campo | Descripción |
|---|---|
| Ejecutable de MT5 | Ruta a `terminal64.exe` — se autodetecta en `Program Files` |
| Carpeta de datos | Carpeta GUID en `AppData\MetaQuotes\Terminal\` — también autodetectada |

Ambos campos muestran `✓` verde cuando la ruta es válida o `✗` rojo si no existe. Cuando la app detecta rutas candidatas las muestra en un combo junto con un botón **Usar esta** que copia esa ruta al campo de arriba con un solo clic.

### Pestaña Telegram

Activa el toggle e ingresa tu `Bot Token` y `Chat ID` para recibir notificaciones. Puedes probar la conexión con el botón **Enviar mensaje de prueba**.

> La configuración se guarda en `config.json` (excluido de git — nunca contiene datos sensibles en el repositorio).

### Ajustes Avanzados (panel colapsable en la ventana principal)

Debajo del panel principal hay un botón **▸ Ajustes Avanzados** que despliega todos los parámetros del Strategy Tester de MT5 — incluyendo lo que antes vivía en la pestaña "Ajustes" de Configuración — sin alterar el comportamiento por defecto de la app hasta que los tocas. Si el contenido no entra en la ventana, la sección hace scroll.

| Campo | Corresponde a | Valores |
|---|---|---|
| Depósito inicial (USD) | `Deposit` | Depósito inicial de la cuenta simulada |
| Apalancamiento | `Leverage` | Ej. `1:100` — siempre inicia en `1:1` al abrir la app |
| Carpeta de informes | — | Ruta donde se guardan los `.html`; si se deja vacío usa `reports/` junto al ejecutable |
| Modelado (Modelling) | `Model` en el `.ini` del tester | `0` Cada tick · `1` OHLC 1 minuto (por defecto, igual que antes) · `2` Solo precio de apertura · `3` Cálculos matemáticos · `4` Cada tick con ticks reales |
| Delay de ejecución (ms) | `ExecutionMode` | `0` normal (por defecto) · `-1` delay aleatorio · `>0` retraso fijo en ms (máx. 600000) |
| Modo visual | `Visual` | Abre el tester en modo visual — más lento, pero necesario para que MT5 dibuje el gráfico de balance en el reporte |

Estos valores se guardan en `config.json` (bajo `common_settings`, `reports_path` y `advanced`) cada vez que corres un backtest, así se recuerdan en la próxima sesión.

### ⚠️ Sobre los gráficos en los reportes `.html`

MT5 genera el reporte HTML del tester **sin la imagen del gráfico de balance/equity cuando corre en modo headless** (`Visual=0`, que es el modo usado por defecto para que el backtest masivo sea rápido) — es una limitación conocida del terminal al automatizarlo por línea de comandos, no un bug de esta app. Para que el `.html` incluya el gráfico, activa **Modo visual** en Ajustes Avanzados: MT5 abrirá una ventana de test por cada EA (más lento) pero el reporte final sí incluirá la imagen.

---

## 💻 Instalación desde código fuente

```bash
# Clonar el repositorio
git clone https://github.com/Sebastianlr11/automata-mt5.git
cd automata-mt5

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python backtester_gui.py
```

> Requiere **Python 3.9+** y **MetaTrader 5** instalado en el sistema (solo compatible con Windows).

---

## 📦 Compilar el .exe

```bash
pyinstaller --onefile --windowed --name "MT5 Backtest Pro" backtester_gui.py
```

El ejecutable queda en `dist/MT5 Backtest Pro.exe`. No requiere Python en el equipo destino.

---

## 📐 Arquitectura

```
automata-mt5/
├── backtester_gui.py     # App completa — UI + lógica de backtesting
├── config.json           # Configuración local (rutas, credenciales) — excluido de git
├── config.example.json   # Plantilla de configuración — comprometido en git
├── requirements.txt      # Dependencias Python
└── README.md
```

**Flujo de trabajo:**

```
config.json (rutas MT5)
        ↓
backtester_gui.py → genera config_batch.ini por cada .ex5
        ↓
MT5 /config:ini → corre el backtest → genera reporte.html
        ↓
App → mueve el .html a la carpeta de informes configurada
        ↓
Telegram → notificación de fin con resumen
```

---

## 🔄 Actualizar la app (instalación existente)

```bash
# En el repositorio local
git pull

# Recompilar el .exe
pyinstaller --onefile --windowed --name "MT5 Backtest Pro" backtester_gui.py
```

O descarga la última versión desde [Releases](https://github.com/Sebastianlr11/automata-mt5/releases).

---

## 📄 Licencia

[MIT](LICENSE) — Libre para uso personal y comercial.
