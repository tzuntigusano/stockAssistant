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
  main.py            app + CORS + startup(init_db×6, monitor, breakout_monitor) + /api/health
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
    breakout_monitor.py  hilo RT: ctx Yahoo/60s + precio Finnhub/8s, NY 9:30-16:00, cooldown 30m
    marketdata.py    intradía pluggable; realtime_prices() Finnhub→Yahoo fallback
    gemini_llm.py    Gemini SSE (reintenta 404/500/503): narrate_stream + converse_stream_tools (function calling update_chart → controla el gráfico) + CHART_TOOL
    llm.py           Ollama local (respaldo): narrate_stream + converse_stream (filtra <think>) + chart_command (JSON forzado → controla el gráfico igual que Gemini)
    notifier.py      notify() = notificación de escritorio MULTIPLATAFORMA (Win toast / macOS osascript / Linux notify-send) + telegram.send()
    telegram.py      bot sendMessage + detect_chats() para averiguar chat_id
    strategy.py      MODULES bilingües (modules(lang)+TEMPLATES) + build_instruction(sel,ticker,lang) + contexto técnico/fundamental/posición + niveles
frontend/src/
  api.ts             cliente tipado (espejo endpoints; añade ?lang= a las peticiones con texto del backend) + streamText(url, onToken, onMeta)
  i18n.ts            useLang() (idioma del store) + currentLang()/localeFor() para helpers de formato
  types.ts           interfaces (espejo de respuestas backend)
  store/useStore.ts  zustand: ticker|view|history(goBack)|radarResult|lang(setLang) + puente chat↔gráfico (chartState publica, applyChartCommand/chartCommand inyecta)
  App.tsx            header (búsqueda, Radar, campana, selector idioma ES/EN) + ruteo ?stock=/?view=
  pages/StockView.tsx  ficha: QuoteHeader, gráfico (toggle TradingView/LiveChart), SentimentPanel,BreakoutPanel,StrategyChat,LotsPanel,AlertsPanel,FeedPanel
  components/*       1 panel = 1 archivo; AlertsBell = campana (rupturas+alertas+toggles)
                     LiveChart = velas propias (lightweight-charts): intervalo+rango (acoplados, sin 1-2 velas), EMAs (longitud+MTF), volumen, BB, RSI, S/R, horario regular/extendido (prepost, esquina inf-dcha, solo intradía). Aplica chartCommand del store (comando (des)marca EMAs, no borra slots)
                     StrategyChat = prompt por módulos (5 dropdowns + preview) + selector modelo (Gemini/Ollama) + chat que CONTROLA el gráfico (gate palabra clave→force_chart, aplica meta.chart). Respuestas en Markdown (react-markdown, clase .md)
                     FeedPanel = muro por acción: publica link de X (tweet incrustado vía widgets.js, tarjeta fallback), imagen (pegar/arrastrar) o texto; nuevas arriba; paginación "Ver más"; editar/borrar
```

## BD (SQLite `backend/data/stocks.db` — persistente, NO borrar)
`cache(key,value,created_at)` · `lots(id,ticker,side,date,price,shares,note)` · `watchlist(ticker)` · `radar_watch(ticker)` · `alerts(id,ticker,type,threshold,note,active)` · `feed_posts(id,ticker,kind,url,text,image,created_at)` (kind: x|image|text; image=fichero en data/feed_images/)

## ENDPOINTS (prefijo /api)
| Ruta | Qué hace |
|---|---|
| GET search?q= · quote/{t} · ohlcv/{t} · news/{t} | datos Yahoo (news ya NO se pinta en la ficha; la IA lo usa para catalizadores) |
| GET chart/{t}?period=&interval=&prepost= · ema/{t}?length=&tf=&period=&interval=&prepost= · price/{t} | LiveChart (velas+ind.; EMA con MTF; precio RT). interval=4h → resample de 60m; prepost=true = horario extendido (intradía) |
| GET analysis/{t}?lang= | quote+indicadores+veredicto diario (veredicto/señales según lang) |
| GET sentiment/{t}?lang= | veredicto 1h/4h/1d (4h = resample de 60m) |
| GET/POST/DELETE lots · GET lots/{t} · GET portfolio | transacciones y cartera |
| GET/POST/DELETE watchlist[/{t}] · radarwatch[/{t}] (+/status/{t}) | listas |
| GET radar/sources?lang= · POST radar?lang= · POST radar/score/{t}?lang= | screener (fuentes/checklist/chips según lang) |
| GET/POST/DELETE alerts · GET alerts/check | alertas clásicas |
| GET notifications/status · POST toggle|test | toasts Windows |
| GET telegram/status|detect · POST telegram/test | móvil |
| GET breakouts/status|recent · POST toggle|scan?force= | radar rupturas RT |
| GET llm/status · models/status | estado IA (gemini_available, ollama_available, model, models[] incl. "ollama") |
| GET strategy/modules?lang= | módulos+opciones+plantilla (en el idioma) para construir el prompt en el front |
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
- ✅ CI: `.github/workflows/ci.yml` (backend `ruff check`+`pytest` en Py3.14; frontend `npm ci`+`typecheck`+`prettier --check`). Deps del backend FIJADAS en `requirements.txt` (yfinance 1.5.1, pandas 3.0.3…) para reproducibilidad.
- ✅ Publicación: `LICENSE` PolyForm Noncommercial 1.0.0. Copia pública saneada regenerable en `C:\Users\Ivan\stock-analyzer-public` (robocopy excluyendo `venv`/`node_modules`/`backend\data`/`.env`/`.claude`/`__pycache__`; verificada sin secretos ni datos personales). Capturas del README pendientes de añadir en `docs/img/` (guía en `docs/img/README.md`; OJO: la cartera muestra posiciones reales).
- ❌ Sin websocket Finnhub (REST polling 8s). Tweets incrustados requieren internet (widgets.js de X). Cobertura de tests parcial (core determinista; no routers/IO).
