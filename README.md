# 📈 Analizador de Acciones

Rastreador y analizador de acciones **local y gratuito**, para uso personal.
Sentimiento alcista/bajista con análisis técnico, gráficos propios y de
TradingView, cotizaciones de Yahoo Finance, precio en tiempo real (Finnhub),
gestión de tus compras (P&L) y un analista con **IA** que redacta el análisis y
responde tus preguntas. Interfaz **bilingüe (ES/EN)**.

Todo corre en tu ordenador. Funciona en **Windows, macOS y Linux**.

> ⚠️ Herramienta informativa de uso personal. **No es asesoramiento financiero.**

---

<!-- CAPTURAS: añade docs/img/analisis.png y docs/img/cartera.png y descomenta
     este bloque (guía en docs/img/README.md). La portada de cartera muestra
     posiciones reales: para la captura pública usa una cartera de ejemplo.

## Capturas

|             Análisis de una acción              |         Cartera y seguimiento          |
| :---------------------------------------------: | :------------------------------------: |
| ![Análisis técnico + IA](docs/img/analisis.png) | ![Cartera con P&L](docs/img/cartera.png) |

---
-->

## Requisitos

- **Python 3.14**
- **Node.js 20+**
- **IA (opcional):**
  - **Gemini** (nube, por defecto): define `GEMINI_API_KEY` en `backend/.env`.
    Modelo por defecto `gemini-2.5-flash` (`GEMINI_MODEL` para cambiarlo).
  - **Ollama** (local, respaldo): corriendo en `http://localhost:11434` con un
    modelo descargado (`OLLAMA_MODEL`, por defecto `qwen3.6:latest`).
  - La app funciona sin IA; solo faltarían los textos generados (veredictos y
    señales son siempre deterministas, no dependen de la IA).
- **Precio en tiempo real (opcional):** `FINNHUB_API_KEY` en `backend/.env`.

Las claves van en `backend/.env` (copia `backend/.env.example`). Nunca se suben
al repositorio.

---

## Instalación guiada (recomendado la primera vez)

Un asistente paso a paso (en **español o inglés**, lo pregunta al arrancar)
comprueba e instala lo necesario (Python, Node.js), prepara el entorno y te pide
las API keys explicándote de dónde sacar cada una. No borra las claves que ya
tengas.

**Windows:** clic derecho en `Instalar.ps1` → **Ejecutar con PowerShell**.

**macOS:** doble clic en `Instalar.command` (o `./instalar.sh` en Terminal).
La primera vez quizá tengas que dar permisos: `chmod +x Instalar.command instalar.sh start.sh`.

**Linux:** `./instalar.sh`.

## Arranque rápido

Una vez instalado, para el día a día:

**Windows** (PowerShell): `.\start.ps1` (o doble clic en `Iniciar-App.bat`).

**macOS / Linux:** `./start.sh` (en macOS también doble clic en `Iniciar-App.command`).

Esto arranca backend y frontend y abre el navegador en `http://localhost:5173`.
El frontend redirige `/api` al backend, así que se arrancan siempre los dos.

### Arranque manual

**Backend:**

```bash
cd backend
# Windows:  .\venv\Scripts\python.exe -m uvicorn main:app --port 8000
# macOS/Linux:  venv/bin/python -m uvicorn main:app --port 8000
```

**Frontend:**

```bash
cd frontend
npm run dev
```

---

## Cómo se usa

1. La portada es **tu cartera**: valores con posición y P&L (realizado y no
   realizado), lista de seguimiento y monitoreo de rupturas en directo. Pulsa
   cualquiera para abrir su análisis.
2. Busca una acción arriba (ej. `AAPL`, `Nokia`, `Santander`).
3. Verás la cotización, el gráfico (TradingView o el **LiveChart** propio con
   EMAs, volumen, Bollinger, RSI, S/R y horario extendido) y el **sentimiento
   técnico** por temporalidad (**1h / 4h / diario**).
4. En **Mis compras y ventas** registra tus operaciones: se calcula tu coste
   medio, tu P&L no realizado y el realizado de las ventas. Se guardan
   permanentemente.
5. Pulsa **Generar estrategia**: la IA redacta el análisis **en directo** (token
   a token) según el técnico, los niveles y tu posición. Eliges el **modelo** en
   el panel: **Gemini** (nube, por defecto) u **Ollama** (local). El **chat**
   integrado mantiene el hilo y además **controla el gráfico por texto**
   ("muéstrame solo la EMA 200 en 4h", "añade volumen", "quita el RSI").
6. En **Alertas** creas avisos (soporte/resistencia, RSI, precio). Saltan en la
   🔔 campana y, si lo activas, lanzan una **notificación de escritorio** (nativa
   en Windows/macOS/Linux) aunque la app esté minimizada, mientras el backend
   siga en marcha.
7. Con **☆ Seguir** añades el valor a tu lista de seguimiento.
8. En el **🔎 Radar** escaneas listas dinámicas de Yahoo y rankeas por
   confluencia de señales de rompimiento (Donchian, volumen, RSI, MACD, ADX,
   EMAs, fuerza relativa, OBV, Bollinger). Todo configurable. **Es un buscador
   para investigar, no una predicción.**
9. **Radar de rupturas en directo:** marca **"🚀 Vigilar rupturas"** en la ficha
   para añadir el valor a una lista aparte. Un vigilante la sondea en horario de
   mercado y, al detectar una **vela de ruptura** (precio rompe el techo reciente
   + pico de volumen + rango grande), avisa al instante. Con `FINNHUB_API_KEY`
   comprueba el precio cada ~8 s en tiempo real; sin ella cae a Yahoo (con
   retraso). Lista pequeña recomendada (≲7 valores) por el límite gratis de
   Finnhub.
10. **Muro por acción (Feed):** publica enlaces de X (tweet incrustado),
    imágenes (pegar/arrastrar) o texto por cada valor, con paginación y
    editar/borrar.
11. **Alertas al móvil (Telegram):** crea un bot con @BotFather, pon
    `TELEGRAM_BOT_TOKEN` en `backend/.env`, reinicia, escríbele "hola", abre
    `http://localhost:8000/api/telegram/detect`, copia tu `chat_id` al `.env` y
    reinicia. Desde entonces toda alerta llega también a Telegram.

---

## Cómo está montado

```
backend/            FastAPI + Python 3.14
  main.py           app + arranque (rutas en routers/)
  settings.py       config; carga backend/.env
  routers/          market · portfolio · ai · screener · alerts · feed (+common)
  core/
    yahoo.py        datos de Yahoo Finance (yfinance)
    cache.py        cache SQLite (evita saturar las APIs)
    i18n.py         L(lang, es, en): textos deterministas bilingües
    indicators.py   RSI, EMAs, MACD, ATR, Bollinger, ADX, OBV (pandas/numpy)
    signals.py      motor de reglas -> veredicto alcista/bajista
    radar.py        screener de rompimientos (universo Yahoo + confluencia)
    breakout.py     detección de vela de ruptura (rotura + volumen + rango)
    breakout_monitor.py  radar en directo (precio Finnhub + contexto Yahoo)
    marketdata.py   precio en tiempo real (Finnhub -> Yahoo fallback)
    lots.py         compras/ventas + P&L (SQLite)
    watchlist.py    listas de seguimiento y monitoreo
    alerts.py       alertas de precio/RSI/niveles
    strategy.py     combina técnico + posición en un contexto (bilingüe)
    gemini_llm.py   cliente de Gemini (streaming + function calling del gráfico)
    llm.py          cliente de Ollama (respaldo local)
    notifier.py     notificación de escritorio multiplataforma + Telegram
    telegram.py     bot de Telegram (opcional)
    feed.py         muro por acción (posts + imágenes)
frontend/           Vite + React + TypeScript + Tailwind
  src/components/    paneles (1 por archivo): gráfico, sentimiento, estrategia,
                     compras, alertas, campana, muro/feed…
  src/pages/         vista de la acción
  src/i18n.ts        idioma del store + helpers de formato por locale
```

**Filosofía:** el veredicto alcista/bajista lo decide el motor de reglas
(determinista y transparente). La IA solo **redacta** sobre datos ya calculados,
nunca elige tickers ni inventa cifras.

### Para IAs / asistentes

Lee `CLAUDE.md` (mapa de contexto) y `ai-rules.md` (reglas de interacción) antes
de tocar código.

### Desarrollo

- Backend: `pip install -r requirements-dev.txt` · lint/formato `ruff check .` /
  `ruff format .` · tests `pytest`.
- Frontend: `npm run typecheck` · `npm run format`.

---

## Licencia

[PolyForm Noncommercial 1.0.0](LICENSE): puedes usar, estudiar y modificar el
código **para fines no comerciales**. No se permite venderlo ni usarlo en un
producto o servicio de pago. Ver el archivo [`LICENSE`](LICENSE) para el texto
completo.

---

## Aviso

Herramienta informativa de uso personal. **No es asesoramiento financiero.** Las
decisiones de inversión son tuyas.
