# stock-analyzer — MAPA DE CONTEXTO

> Regla nº1 para IAs: lee este archivo y `ai-rules.md` ANTES de explorar nada.
> Responde en castellano. Edita con diffs mínimos. No reescribas archivos enteros.

## QUÉ ES
App LOCAL y GRATUITA de análisis bursátil personal (1 usuario, Windows). Bilingüe ES/EN (selector arriba-dcha). No es asesoramiento financiero.
- Stack: FastAPI + Python 3.14 (`backend/venv`) · Vite + React 18 + TS + Tailwind 4 · SQLite
- i18n: idioma en `store.lang` (localStorage `sa_lang`); front traduce con objetos `T={es,en}` colocados por componente (`useLang()` de `i18n.ts`; formatos vía locale). Backend genera texto según `lang`: helper `core/i18n.py` `L(lang,es,en)` + `lang_directive`; endpoints aceptan `?lang=` / body `lang`. La IA responde en ese idioma (system prompt + directiva en el último turno)
- IA = Gemini (nube, por defecto) + Ollama (local, respaldo). Solo REDACTA, nunca decide. `GEMINI_API_KEY` + `GEMINI_MODEL` (def. gemini-2.5-flash) + `OLLAMA_MODEL` (def. qwen3.6) en `.env`; modelo elegible en el front (incl. "ollama"). Free tier Gemini MUY limitado (429 rápido). El chat controla el gráfico por texto con AMBOS (Gemini function calling / Ollama JSON)
- Veredictos/señales = SIEMPRE deterministas (`core/signals.py`, `core/radar.py`, `core/breakout.py`)
- Datos: yfinance (gratis, retraso) + Finnhub (precio tiempo real, `FINNHUB_API_KEY`)
- Instalación guiada 1ª vez, BILINGÜE ES/EN (pregunta idioma al inicio; helper `T(es,en)`/`t()`): Windows `Instalar.ps1` · macOS `Instalar.command`/`instalar.sh` · Linux `instalar.sh` (comprueba/instala Python+Node vía winget/brew, monta venv+npm, asistente de API keys que CONSERVA claves existentes y preserva vars desconocidas; escribe `backend/.env`). Plantilla `backend/.env.example`. OJO Win: los `.ps1` con acentos necesitan BOM UTF-8 o PS 5.1 los rompe (comillas tipográficas)
- Arranque: Windows `.\start.ps1` (o `Iniciar-App.bat`) · macOS/Linux `./start.sh` (o `Iniciar-App.command`, hace setup la 1ª vez) → backend :8000 + frontend :5173 (proxy `/api`). Multiplataforma (Win/macOS/Linux); `windows-toasts` solo se instala en Windows

## ARQUITECTURA
```
backend/
  main.py            app + CORS + startup(init_db×7, monitor, breakout_monitor, setup_monitor, paper_monitor) + /api/health
  settings.py        config; carga backend/.env (GEMINI_*, OLLAMA_*, FINNHUB_API_KEY, TELEGRAM_*)
  routers/           market | portfolio | ai | screener | alerts | feed (+common: analyze/strategy_data/chat_context)
  core/
    yahoo.py         quotes/ohlcv(prepost)/news/search + get_fundamentals (yfinance 1.5; news anidado en 'content')
    cache.py         SQLite cache TTL: quote 5m, ohlcv 15m, news 30m, fundamentals 6h
    feed.py          muro por acción (posts X/imagen/texto); imágenes en data/feed_images/
    i18n.py          L(lang,es,en) + lang_directive(lang) para textos deterministas + idioma IA
    indicators.py    RSI,EMA,MACD,ATR,Bollinger,ADX,OBV a mano (pandas-ta ROTO en Py3.14)
    signals.py       reglas → {score 0-100, label, signals[]} (evaluate(ind, lang) bilingüe)
    lots.py          compras/ventas coste medio; P&L realizado y no realizado
    watchlist.py|radarwatch.py  listas separadas: seguimiento general vs monitoreo RT
    alerts.py|scanner.py|monitor.py  alertas precio/RSI/niveles + hilo vigilante (120s)
    radar.py         screener: yf.screen(day_gainers…) + confluencia 10 señales, pesos/umbrales config (labels bilingües; ¡ojo: no shadowear la función L!)
    breakout.py      context(bars) + is_breakout(ctx, precio_vivo) — rotura+volumen+expansión
    elliott.py       ONDAS DE ELLIOTT deterministas: zigzag(bars,threshold) → pivotes alternos; _try_impulse barre ventanas buscando dónde encaja un 1-5 válido y DESCARTA lo que viole las 3 reglas duras (r1 onda2≤100% de la 1, r2 la 3 no es la más corta, r3 la 4 no solapa la 1); fallback A-B-C; niveles Fibonacci de la onda en curso; summarize() da el texto que NARRA la IA (nunca lo inventa)
    trendlines.py    detección de líneas de tendencia (pivotes swing → ajuste → validación por cierres → candidatas cercanas al precio); endpoint /trendlines dibuja y da anclas para congelar
    breakout_monitor.py  hilo RT: ctx Yahoo/60s + precio Finnhub/8s, NY 9:30-16:00, cooldown 30m
    setup.py|setup_store.py|setup_monitor.py  ALERTA DE SETUP: máquina de estados determinista rotura→retest→rebote+volumen (largos y cortos; nivel ENCHUFABLE: EMA o trendline congelada vía anclas en `line`); `advance(...,level,prev_level)` agnóstico; estado persistido (sobrevive reinicios); hilo vigila cada 120s y notifica DISTINTO por fase (bilingüe vía `lang` guardado)
    paper.py         CARTERAS FICTICIAS: motor de decisión DETERMINISTA y puro (sin BD ni red). Ambas arrancan con 1.000 $. MODES normal (swing, riesgo 0.6%, stop 2×ATR, objetivo 2.5R, 8 pos.) y fast (intradía, riesgo 0.35%, stop 1.5%, objetivo 3%, 4 pos., `let_winners_run`); plan_entry() (dirección por alineación EMA20/50, tamaño por riesgo, stop/objetivo, mínimo de posición RELATIVO al equity) + check_exit() (stop→objetivo→tesis rota→plazo, con break-even a 1R y trailing a 1.5R). En la rápida, al tocar el objetivo NO cierra si `still_trending()` (precio>EMA20 + MACD>0 + RSI≥55, las tres): sube el stop y marca la posición como `runner`; cierra en cuanto se rompe una pata. Ningún LLM decide (regla nº1)
    paper_store.py   persistencia: caja por cartera, posiciones (abiertas/cerradas con stop/objetivo/tesis) y DIARIO (incluye los ciclos sin operar y por qué)
    paper_engine.py  orquestador: revisa abiertas → candidatos (radar.scan + watchlist, tope 12) → abre (máx. 3/2 por ciclo). Normal usa velas 1d; fast, 15m. run_cycle(execute=) SOLO ejecuta con market_open(); cerrado = simulacro (eventos kind='dryrun', no toca cartera ni caja). summary()/compare()
    paper_monitor.py hilo: ciclo cada 15 min mientras market_open() y la app encendida (primer ciclo al arrancar); notifica aperturas/cierres; run_once() serializado con lock
    marketdata.py    intradía pluggable; realtime_prices() Finnhub→Yahoo fallback
    gemini_llm.py    Gemini SSE (reintenta 404/500/503): narrate_stream + converse_stream_tools (function calling update_chart → controla el gráfico) + CHART_TOOL
    llm.py           Ollama local (respaldo): narrate_stream + converse_stream (filtra <think>) + chart_command (JSON forzado → controla el gráfico igual que Gemini)
    notifier.py      notify() = notificación de escritorio MULTIPLATAFORMA (Win toast / macOS osascript / Linux notify-send) + telegram.send()
    telegram.py      bot sendMessage + detect_chats() para averiguar chat_id
    (El conteo de Elliott entra en el contexto de la IA vía `common.elliott_context()`: se añade al técnico en strategy/{t} y al chat/{t}. NO se incluye en el informe de cartera para no inflar el prompt)
    strategy.py      MODULES bilingües (modules(lang)+TEMPLATES) + build_instruction(sel,ticker,lang) + contexto técnico/fundamental/posición + niveles
frontend/src/
  api.ts             cliente tipado (espejo endpoints; añade ?lang= a las peticiones con texto del backend) + streamText(url, onToken, onMeta). Limitador de concurrencia (gate, MAX_CONCURRENT=2) en las llamadas a Yahoo (analysis/sentiment/chart/ema/radarScoreOne): escalona la ráfaga en frío (evita 429), instantáneo en caliente. onPendingData() alimenta el aviso DataLoadingBanner (sale si tarda >600ms)
  i18n.ts            useLang() (idioma del store) + currentLang()/localeFor() para helpers de formato
  types.ts           interfaces (espejo de respuestas backend)
  store/useStore.ts  zustand: ticker|view|history(goBack)|radarResult|lang(setLang) + puente chat↔gráfico (chartState publica, applyChartCommand/chartCommand inyecta)
  App.tsx            header (búsqueda, Radar, Alertas, campana, ⟳ reiniciar, selector idioma ES/EN) + ruteo ?stock=/?view=
  pages/StockView.tsx  ficha: QuoteHeader, gráfico (toggle TradingView/LiveChart), SentimentPanel,BreakoutPanel,StrategyChat,LotsPanel,AlertsPanel,FeedPanel
  components/*       1 panel = 1 archivo; AlertsBell = campana (rupturas+alertas+toggles)
                     AlertsView = vista central (view="alerts", botón 🔔 Alertas del header): lista TODAS las alertas (clásicas + setups) de todos los valores, con pausar/activar individual, MASIVO (⏸/▶ todas) y borrar; el ticker abre su ficha
                     RestartButton = ⟳ en el header: POST /system/restart, espera /health y recarga (arregla la sesión degradada de yfinance)
                     LiveChart = velas propias (lightweight-charts): intervalo+rango (acoplados, sin 1-2 velas), EMAs (longitud+MTF), volumen, BB, RSI, S/R, trendlines (toggle), ELLIOTT (toggle: polilínea + etiquetas por marcadores + fibos), MI MEDIA (coste medio de mis compras, prop `avgPrice` desde StockView; checkbox solo si hay posición), horario regular/extendido (prepost, esquina inf-dcha, solo intradía), PANTALLA COMPLETA (botón ⛶ / Esc: overlay fixed, la caja pasa a flex-1). Aplica chartCommand del store (comando (des)marca EMAs, no borra slots)
                     StrategyChat = prompt por módulos (5 dropdowns + preview) + selector modelo (Gemini/Ollama) + ÁMBITO (Stock actual / Todos mis stocks → POST strategy-all/stream; en modo cartera se ocultan los módulos y el chat posterior sigue atado al valor abierto) + chat que CONTROLA el gráfico (gate palabra clave→force_chart, aplica meta.chart). Respuestas en Markdown (react-markdown, clase .md)
                     PaperView = vista central (view="paper", botón 🧪 Ficticias del header): las DOS carteras ficticias lado a lado con su comparativa (equity, P&L, % acierto, chip 🏆 al líder), posiciones abiertas con entrada/actual/STOP/OBJETIVO/R:R/tesis/días (clic en el ticker → su ficha; botón 🔔 crea alertas reales con el objetivo y el stop; botón cerrar), cerradas con motivo de salida, y el DIARIO. Botón «Re-analizar ahora» + toggle del automático + estado del mercado USA
                     FeedPanel = muro por acción: publica link de X (tweet incrustado vía widgets.js, tarjeta fallback), imagen (pegar/arrastrar) o texto; nuevas arriba; paginación "Ver más"; editar/borrar
```

## BD (SQLite `backend/data/stocks.db` — persistente, NO borrar)
`cache(key,value,created_at)` · `lots(id,ticker,side,date,price,shares,note)` · `watchlist(ticker)` · `radar_watch(ticker)` · `alerts(id,ticker,type,threshold,note,active)` · `feed_posts(id,ticker,kind,url,text,image,created_at)` (kind: x|image|text; image=fichero en data/feed_images/) · `paper_portfolios(mode,cash,initial_cash,created_at)` · `paper_positions(id,mode,ticker,side,shares,entry_price,entry_at,stop,initial_stop,target,rr,horizon,thesis,score,stop_moved,status,exit_*,pnl)` · `paper_log(id,mode,at,kind,ticker,text)` (kind: entry|exit|stop|skip|cycle|system)

## ENDPOINTS (prefijo /api)
| Ruta | Qué hace |
|---|---|
| GET search?q= · quote/{t} · ohlcv/{t} · news/{t} | datos Yahoo (news ya NO se pinta en la ficha; la IA lo usa para catalizadores) |
| GET chart/{t}?period=&interval=&prepost= · ema/{t}?length=&tf=&period=&interval=&prepost= · price/{t} | LiveChart (velas+ind.; EMA con MTF; precio RT). interval=4h → resample de 60m; prepost=true = horario extendido (intradía) |
| GET elliott/{t}?period=&interval=&prepost=&threshold= | conteo de ondas: `points` (polilínea), `labels` (marcadores 1-5/A-B-C), `fibs` (niveles de la onda en curso), `rules` y `confidence`. `found:false` si ningún conteo cumple las reglas |
| GET trendlines/{t}?period=&interval=&prepost= | líneas de tendencia: `points` (dibujo, formato de las velas) + `anchors` (ts absolutos, para congelar en una alerta) |
| GET analysis/{t}?lang= | quote+indicadores+veredicto diario (veredicto/señales según lang) |
| GET sentiment/{t}?lang= | veredicto 1h/4h/1d (4h = resample de 60m) |
| GET/POST/PATCH/DELETE lots · GET lots/{t} · GET portfolio | transacciones y cartera. `PATCH /lots/{id}` edita parcialmente (precio/acciones/side/fecha/nota); el coste medio y el P&L se recalculan solos porque `summarize()` siempre recorre las filas actuales |
| GET/POST/DELETE watchlist[/{t}] · radarwatch[/{t}] (+/status/{t}) | listas |
| GET radar/sources?lang= · POST radar?lang= · POST radar/score/{t}?lang= | screener (fuentes/checklist/chips según lang) |
| GET/POST/DELETE alerts · GET alerts/check · POST alerts/{id}/toggle · POST alerts/toggle-all | alertas clásicas (toggle individual y MASIVO sin borrar; `toggle-all` admite `ticker` para limitar) |
| GET/POST/DELETE setups · POST setups/{id}/toggle · POST setups/toggle-all · GET setups/recent\|status · POST setups/scan | alertas de SETUP (rotura→retest→rebote+vol); estado persistido, aviso distinto por fase |
| GET paper?lang= · paper/{mode}?lang= · paper/status · paper/log?mode=&limit= · paper/recent | CARTERAS FICTICIAS: comparativa de las dos, una sola, estado del hilo, diario y eventos recientes |
| POST paper/run · paper/toggle · paper/reset/{mode} · paper/positions/{id}/close · paper/positions/{id}/alerts | re-análisis MANUAL (con el mercado CERRADO hace SIMULACRO: analiza y anota en el diario lo que haría, sin ejecutar — fuera de horario solo hay el precio del último cierre; 409 si ya hay uno en curso), on/off del automático, reinicio de la cartera, cierre manual de una posición y creación de alertas REALES con su objetivo y su stop |
| GET health · POST system/restart | salud + reinicio del backend (re-exec de uvicorn; arregla la sesión degradada de yfinance sin abrir terminal). Botón ⟳ en la cabecera (RestartButton: confirma, espera /health, recarga) |
| GET notifications/status · POST toggle|test | toasts Windows |
| GET telegram/status|detect · POST telegram/test | móvil |
| GET breakouts/status|recent · POST toggle|scan?force= | radar rupturas RT |
| GET llm/status · models/status | estado IA (gemini_available, ollama_available, model, models[] incl. "ollama") |
| GET strategy/modules?lang= | módulos+opciones+plantilla (en el idioma) para construir el prompt en el front |
| POST strategy-all/stream · chat-all/stream | INFORME DE CARTERA: una sola llamada a la IA con los datos deterministas (técnico + posición) de cada valor con posición abierta (tope 15); devuelve un informe con sección por valor + visión de conjunto. `chat-all` usa ESE MISMO contexto para que el chat entienda toda la cartera (sin control del gráfico: chart=null). Helper compartido `_portfolio_blocks()`. Rutas sin `{ticker}` a propósito, para no chocar con strategy/{t} y chat/{t} |
| POST strategy/{t}/stream · chat/{t}/stream | IA (Gemini u Ollama según model). Body estrategia: {selections,model,lang}. Body chat: {history,model,chart_state,force_chart,lang}. chat meta 1ª línea = {chart: cfg\|null}: si cfg, orden update_chart {interval?,emas?,indicators?} → LiveChart |
| GET feed/{t}?offset=&limit= · POST feed/{t} · PATCH/DELETE feed/{id} · GET feed/image/{name} | muro por acción (posts + imágenes) |

## REGLAS CRÍTICAS (no romper)
1. El LLM NUNCA elige tickers ni veredictos (alucinaría). Solo redacta sobre datos calculados.
2. `yf.download` devuelve columnas MultiIndex incluso con 1 ticker → usar `marketdata._extract`.
3. Finnhub free ≤60 llam/min → `breakout_monitor._interval()` auto-ajusta; radar RT ≲7 tickers.
4. Protocolo streaming: línea 1 = meta JSON + `"\n\n"` + texto (parseado por `streamText` en api.ts). En /chat la meta lleva {chart}.
5. Claves en `backend/.env` (gitignored). Nunca hardcodear ni subir.
6. UI: dark, variables CSS `--color-*` (index.css). TODO texto de cara al usuario BILINGÜE: front con `T={es,en}` + `useLang()`; backend con `L(lang,es,en)`. Nada hardcodeado en un solo idioma. Al añadir texto del backend, pásalo por `lang` y añade `?lang=`/deps `lang` en el front para que se recargue.
7. Cambios backend requieren reiniciar uvicorn (sin --reload en producción local). Frontend: HMR.
8. Windows + PowerShell 5.1 (sin `&&`); rutas de prueba con `Invoke-RestMethod`.
9. Gemini free tier se agota enseguida (429) y da 404/503 transitorios. `gemini_llm._sse_lines` reintenta 404/500/503 (NO 429). No hagas ráfagas de pruebas: quemarías la cuota del usuario.

## ESTADO (2026-07-13)
- ✅ MVP completo: ficha (gráfico TV + LiveChart propio, sentimiento multi-TF, breakout score, estrategia+chat IA, compras/ventas P&L, alertas, muro/feed), cartera con enlaces, screener configurable, radar rupturas RT (Finnhub), toasts persistentes + Telegram, navegación atrás, abrir en pestaña (?stock=).
- ✅ LiveChart (lightweight-charts 4.2.3): intervalo (incl. 4h) + rango acoplados (nunca 1-2 velas), EMAs longitud+MTF, volumen, BB, RSI, S/R, precio vivo Finnhub, horario regular/extendido (prepost) en intradía.
- ✅ IA: Gemini (def.) + Ollama (respaldo local). Reporte por módulos (Análisis/Posición/Temporalidad[incl. "cualquiera"]/Objetivo/Formato) con preview + chat. Fundamentales ricos + titulares. Respuestas en Markdown. Claude eliminado; Pro fuera del selector.
- ✅ Chat controla el gráfico por texto con AMBOS motores (Gemini function calling / Ollama JSON): "muéstrame solo la EMA 200 en 4h", "añade volumen", "quita el RSI". "muéstrame X" = solo esa (des)marcando checkboxes, sin borrar slots. Probado e2e.
- ✅ Muro/feed por acción (sustituye Noticias): links de X (tweet incrustado), imágenes (pegar/arrastrar) y texto; paginación, editar/borrar. Probado e2e.
- ✅ Bilingüe ES/EN completo (selector arriba-dcha): toda la UI + textos deterministas del backend (veredicto, señales, checklist radar, módulos) + la IA responde en el idioma elegido (Gemini y Ollama). Probado e2e. Pendiente: mensajes de la campana (alertas/rupturas) siguen en español (se generan en hilos de fondo).
- 🔶 Telegram operativo (bot creado, TELEGRAM_* rellenos); notificaciones confirmadas.
- ✅ Tooling profesional: back `ruff` + `pytest` (config en `backend/pyproject.toml`, deps en `requirements-dev.txt`, 20 tests del core determinista en `backend/tests/`); front `prettier` (`.prettierrc.json`) + scripts `format`/`typecheck`. Raíz: `.gitattributes` (LF en `.sh`/`.command`, CRLF en `.ps1`/`.bat`) + `.editorconfig`. LiveChart partido: `liveChartConfig.ts` (constantes/tipos/helpers) + `EmaSettings.tsx` (panel EMAs); el componente queda centrado en la lógica del gráfico.
- ✅ Alerta de SETUP (rotura de EMA → retest → rebote con volumen): máquina de estados determinista `core/setup.py` (largos y cortos, nivel EMA "enchufable", 9 tests), persistida en `setup_store`, hilo `setup_monitor` que avisa DISTINTO en cada fase (Fase 1 rotura / Fase 2 retest / Fase 3 rebote+vol, escritorio+Telegram bilingüe), panel `SetupAlertsPanel` en la ficha (armar/pausar/borrar + fase en color). Nivel EMA **o TRENDLINE**: detección determinista (`core/trendlines.py`, candidatas cercanas al precio), toggle "Tendencias" en el LiveChart (discontinuas), y al armar eliges una línea detectada que se CONGELA (anclas) y se vigila con el mismo motor. Probado e2e (largos/cortos, EMA y trendline).
- ✅ Carteras ficticias (paper trading, 2026-07-19): DOS carteras compitiendo (normal swing / muy corto plazo) con dinero simulado. Motor 100% determinista (`core/paper.py`, 22 tests): elige del radar, dimensiona por riesgo, fija stop y objetivo al entrar y sale por stop / objetivo / tesis invalidada / plazo, con break-even a 1R y trailing a 1.5R. Hilo automático cada 15 min con el mercado USA abierto + botón «Re-analizar ahora» (vale con el mercado cerrado). Vista `PaperView` con comparativa, diario (anota también por qué NO opera) y, desde cada posición, salto a la ficha y creación de alertas reales con su objetivo/stop. Probado e2e.
- ✅ CI: `.github/workflows/ci.yml` (backend `ruff check`+`pytest` en Py3.14; frontend `npm ci`+`typecheck`+`prettier --check`). Deps del backend FIJADAS en `requirements.txt` (yfinance 1.5.1, pandas 3.0.3…) para reproducibilidad.
- ✅ Publicación: `LICENSE` PolyForm Noncommercial 1.0.0. Copia pública saneada regenerable en `C:\Users\Ivan\stock-analyzer-public` (robocopy excluyendo `venv`/`node_modules`/`backend\data`/`.env`/`.claude`/`__pycache__`; verificada sin secretos ni datos personales). Capturas del README pendientes de añadir en `docs/img/` (guía en `docs/img/README.md`; OJO: la cartera muestra posiciones reales).
- ❌ Sin websocket Finnhub (REST polling 8s). Tweets incrustados requieren internet (widgets.js de X). Cobertura de tests parcial (core determinista; no routers/IO).
