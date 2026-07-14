import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type IPriceLine,
} from "lightweight-charts";
import { api } from "../api";
import { useStore } from "../store/useStore";
import { useLang } from "../i18n";
import type { ChartBundle, LinePoint, TrendLine } from "../types";
import EmaSettings from "./EmaSettings";
import {
  allowedRanges,
  C,
  DEFAULT_EMAS,
  DEFAULT_OPTS,
  DEFAULT_RANGE_FOR,
  type Ema,
  EMA_PALETTE,
  INTERVALS,
  INTRADAY,
  K,
  load,
  type Opts,
  RANGES,
  RANK,
} from "./liveChartConfig";

const TX = {
  es: {
    emaTfTitle: "Timeframe de la EMA (MTF)",
    removeEma: "Quitar esta EMA",
    addEma: "+ Añadir EMA",
    tfNote: 'TF = temporalidad de la EMA. "—" usa la del gráfico.',
    volume: "Volumen",
    trendlines: "Tendencias",
    refreshTitle: "Refrescar datos",
    refresh: "Refrescar",
    sessionTitleOn: "Horario regular vs extendido (pre-market + after-hours)",
    sessionTitleOff: "El horario extendido solo aplica en intradía (5m–4h)",
    regular: "Regular",
    extended: "Extendido",
  },
  en: {
    emaTfTitle: "EMA timeframe (MTF)",
    removeEma: "Remove this EMA",
    addEma: "+ Add EMA",
    tfNote: 'TF = EMA timeframe. "—" uses the chart\'s.',
    volume: "Volume",
    trendlines: "Trendlines",
    refreshTitle: "Refresh data",
    refresh: "Refresh",
    sessionTitleOn: "Regular vs extended hours (pre-market + after-hours)",
    sessionTitleOff: "Extended hours only apply intraday (5m–4h)",
    regular: "Regular",
    extended: "Extended",
  },
} as const;

export default function LiveChart({ symbol }: { symbol: string }) {
  const tt = TX[useLang()];
  const [opts, setOpts] = useState<Opts>(() => load(K.opts, DEFAULT_OPTS));
  const [emas, setEmas] = useState<Ema[]>(() => {
    try {
      const raw = localStorage.getItem(K.emas);
      return raw ? JSON.parse(raw) : DEFAULT_EMAS;
    } catch {
      return DEFAULT_EMAS;
    }
  });
  const [interval, setIntervalV] = useState<string>(() => localStorage.getItem(K.interval) || "1d");
  const [range, setRange] = useState<string>(() => localStorage.getItem(K.range) || "1A");
  const [session, setSession] = useState<"regular" | "extended">(
    () => (localStorage.getItem(K.session) as "regular" | "extended") || "regular"
  );
  const [reloadKey, setReloadKey] = useState(0);
  const [loading, setLoading] = useState(false);
  const [emaPanel, setEmaPanel] = useState(false);
  const [bundle, setBundle] = useState<ChartBundle | null>(null);
  const [emaData, setEmaData] = useState<Record<number, LinePoint[]>>({});
  const [trendlines, setTrendlines] = useState<TrendLine[]>([]);
  const [rtPrice, setRtPrice] = useState<number | null>(null);
  const [realtime, setRealtime] = useState(false);

  const boxRef = useRef<HTMLDivElement>(null);
  const rsiBoxRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const overlaysRef = useRef<ISeriesApi<"Line" | "Histogram">[]>([]);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const lastCandleRef = useRef<ChartBundle["candles"][number] | null>(null);

  const setChartState = useStore((s) => s.setChartState);
  const chartCommand = useStore((s) => s.chartCommand);

  // Resuelve el periodo efectivo: el intervalo manda; si el rango no vale para
  // ese intervalo, cae al rango por defecto (nunca a 1-2 velas).
  const okRanges = allowedRanges(interval);
  const effRange = okRanges.includes(range)
    ? range
    : (DEFAULT_RANGE_FOR[interval] ?? okRanges[okRanges.length - 1]);
  const period = RANGES.find((r) => r.key === effRange)!.period;

  // Horario extendido solo pinta datos distintos en intradía.
  const showSession = INTRADAY.has(interval);
  const prepost = showSession && session === "extended";

  function pickSession(s: "regular" | "extended") {
    localStorage.setItem(K.session, s);
    setSession(s);
  }

  function persistOpts(next: Opts) {
    localStorage.setItem(K.opts, JSON.stringify(next));
    setOpts(next);
  }
  function toggleOpt(k: keyof Opts) {
    persistOpts({ ...opts, [k]: !opts[k] });
  }
  function persistEmas(next: Ema[]) {
    localStorage.setItem(K.emas, JSON.stringify(next));
    setEmas(next);
  }
  function editEma(id: number, patch: Partial<Ema>) {
    persistEmas(emas.map((e) => (e.id === id ? { ...e, ...patch } : e)));
  }
  function addEma() {
    const usedColors = new Set(emas.map((e) => e.color));
    const color =
      EMA_PALETTE.find((c) => !usedColors.has(c)) ?? EMA_PALETTE[emas.length % EMA_PALETTE.length];
    const usedLen = new Set(emas.map((e) => e.length));
    const length = [9, 20, 50, 100, 150, 200].find((l) => !usedLen.has(l)) ?? 20;
    const id = emas.reduce((m, e) => Math.max(m, e.id), 0) + 1;
    persistEmas([...emas, { id, on: true, length, tf: "", color }]);
  }
  function removeEma(id: number) {
    persistEmas(emas.filter((e) => e.id !== id));
  }
  function pickRange(k: string) {
    localStorage.setItem(K.range, k);
    setRange(k);
  }
  function pickInterval(k: string) {
    localStorage.setItem(K.interval, k);
    setIntervalV(k);
    // Si el rango actual no vale para el nuevo intervalo, pon uno sensato.
    if (!allowedRanges(k).includes(range)) pickRange(DEFAULT_RANGE_FOR[k] ?? "1A");
  }

  // Publica el estado del gráfico al store (para que el chat sepa qué hay).
  useEffect(() => {
    const emaOn = emas
      .filter((e) => e.on)
      .map((e) => `EMA${e.length}${e.tf ? ` MTF ${e.tf}` : ""}`);
    const inds = (["volume", "bollinger", "rsi", "levels"] as (keyof Opts)[]).filter(
      (k) => opts[k]
    );
    const ivLabel = INTERVALS.find((i) => i.key === interval)?.label ?? interval;
    setChartState(
      `intervalo=${ivLabel}; emas=[${emaOn.join(", ") || "ninguna"}]; ` +
        `indicadores=[${inds.join(", ") || "ninguno"}]`
    );
  }, [interval, emas, opts, setChartState]);

  // Aplica un comando del chat (estado completo deseado del gráfico).
  useEffect(() => {
    if (!chartCommand) return;
    const c = chartCommand;
    const iv = c.interval && INTERVALS.some((i) => i.key === c.interval) ? c.interval : interval;
    if (c.interval && iv !== interval) pickInterval(iv);
    if (c.emas !== undefined) {
      const norm = (tf: string) => (tf && (RANK[tf] ?? 9) <= (RANK[iv] ?? 0) ? "" : tf); // no MTF si no es mayor
      const desired = c.emas.map((e) => ({
        length: Math.max(1, Math.min(400, Math.round(e.length) || 20)),
        tf: norm(e.tf || ""),
      }));
      // Conserva los slots existentes: solo (des)marca su checkbox según el objetivo.
      const next: Ema[] = emas.map((slot) => ({
        ...slot,
        on: desired.some((d) => d.length === slot.length && d.tf === (slot.tf || "")),
      }));
      // Añade como slot nuevo solo las EMAs pedidas que no existían.
      let nextId = emas.reduce((m, e) => Math.max(m, e.id), 0);
      desired.forEach((d) => {
        if (!next.some((slot) => slot.length === d.length && (slot.tf || "") === d.tf)) {
          nextId += 1;
          next.push({
            id: nextId,
            on: true,
            length: d.length,
            tf: d.tf,
            color: EMA_PALETTE[next.length % EMA_PALETTE.length],
          });
        }
      });
      persistEmas(next);
    }
    if (c.indicators !== undefined) {
      const wanted = c.indicators;
      // Solo tocamos los indicadores que controla el chat; trendlines se conserva.
      setOpts((cur) => {
        const next: Opts = { ...cur, volume: false, bollinger: false, levels: false, rsi: false };
        wanted.forEach((k) => {
          if (k in next && k !== "trendlines") next[k as keyof Opts] = true;
        });
        localStorage.setItem(K.opts, JSON.stringify(next));
        return next;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chartCommand]);

  // Crea el gráfico y carga las velas al cambiar valor / intervalo / rango / refrescar.
  useEffect(() => {
    const box = boxRef.current;
    if (!box) return;
    const chart = createChart(box, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: C.bg }, textColor: C.text },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: C.grid },
      timeScale: { borderColor: C.grid, timeVisible: true },
    });
    const candle = chart.addCandlestickSeries({
      upColor: C.bull,
      downColor: C.bear,
      borderVisible: false,
      wickUpColor: C.bull,
      wickDownColor: C.bear,
    });
    chartRef.current = chart;
    candleRef.current = candle;

    setBundle(null);
    setLoading(true);
    api
      .chart(symbol, period, interval, prepost)
      .then((b) => {
        candle.setData(b.candles as any);
        lastCandleRef.current = b.candles[b.candles.length - 1] ?? null;
        chart.timeScale().fitContent();
        setBundle(b);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    return () => {
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      overlaysRef.current = [];
      priceLinesRef.current = [];
    };
  }, [symbol, interval, period, prepost, reloadKey]);

  // Pide cada EMA activa (con debounce para no spamear al escribir la longitud).
  useEffect(() => {
    const active = emas.filter((e) => e.on && e.length > 0);
    const handle = setTimeout(async () => {
      const results: Record<number, LinePoint[]> = {};
      await Promise.all(
        active.map(async (e) => {
          try {
            const r = await api.ema(symbol, {
              length: e.length,
              tf: e.tf,
              period,
              interval,
              prepost,
            });
            results[e.id] = r.points;
          } catch {
            results[e.id] = [];
          }
        })
      );
      setEmaData(results);
    }, 350);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval, period, prepost, reloadKey, JSON.stringify(emas)]);

  // Líneas de tendencia (solo cuando están activadas).
  useEffect(() => {
    if (!opts.trendlines) {
      setTrendlines([]);
      return;
    }
    let cancelled = false;
    api
      .trendlines(symbol, period, interval, prepost)
      .then((r) => !cancelled && setTrendlines(r.lines))
      .catch(() => !cancelled && setTrendlines([]));
    return () => {
      cancelled = true;
    };
  }, [symbol, interval, period, prepost, reloadKey, opts.trendlines]);

  // Reconcilia overlays: EMAs (de emaData), Bollinger, volumen y niveles.
  useEffect(() => {
    const chart = chartRef.current;
    const candle = candleRef.current;
    if (!chart || !candle || !bundle) return;

    overlaysRef.current.forEach((s) => chart.removeSeries(s));
    overlaysRef.current = [];
    priceLinesRef.current.forEach((pl) => candle.removePriceLine(pl));
    priceLinesRef.current = [];

    const addLine = (data: any[], color: string, width = 2, lineStyle = 0) => {
      if (!data || !data.length) return;
      const s = chart.addLineSeries({
        color,
        lineWidth: width as any,
        lineStyle: lineStyle as any,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s.setData(data);
      overlaysRef.current.push(s);
    };

    emas.forEach((e) => {
      if (e.on) addLine(emaData[e.id], e.color);
    });
    if (opts.bollinger) {
      addLine(bundle.bb_upper, C.bb, 1);
      addLine(bundle.bb_lower, C.bb, 1);
    }
    if (opts.volume) {
      const vol = chart.addHistogramSeries({
        priceScaleId: "vol",
        priceFormat: { type: "volume" },
        lastValueVisible: false,
      });
      chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      vol.setData(
        bundle.volume.map((v) => ({
          time: v.time as any,
          value: v.value,
          color: v.up ? "rgba(34,197,94,0.5)" : "rgba(239,68,68,0.5)",
        }))
      );
      overlaysRef.current.push(vol);
    }
    if (opts.trendlines) {
      // Discontinuas: soporte en verde, resistencia en rojo.
      trendlines.forEach((tl) => addLine(tl.points, tl.kind === "support" ? C.bull : C.bear, 2, 2));
    }
    if (opts.levels) {
      if (bundle.support)
        priceLinesRef.current.push(
          candle.createPriceLine({
            price: bundle.support,
            color: C.bull,
            lineWidth: 1,
            lineStyle: 2,
            title: "Soporte",
          } as any)
        );
      if (bundle.resistance)
        priceLinesRef.current.push(
          candle.createPriceLine({
            price: bundle.resistance,
            color: C.bear,
            lineWidth: 1,
            lineStyle: 2,
            title: "Resistencia",
          } as any)
        );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bundle, emaData, opts, trendlines, JSON.stringify(emas)]);

  // RSI en un mini-panel separado.
  useEffect(() => {
    const box = rsiBoxRef.current;
    if (!box || !opts.rsi || !bundle || !bundle.rsi.length) return;
    const chart = createChart(box, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: C.bg }, textColor: C.text },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      rightPriceScale: { borderColor: C.grid },
      timeScale: { borderColor: C.grid, visible: false },
    });
    const s = chart.addLineSeries({ color: "#eab308", lineWidth: 2, priceLineVisible: false });
    s.setData(bundle.rsi as any);
    s.createPriceLine({ price: 70, color: C.bear, lineWidth: 1, lineStyle: 2, title: "70" } as any);
    s.createPriceLine({ price: 30, color: C.bull, lineWidth: 1, lineStyle: 2, title: "30" } as any);
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [opts.rsi, bundle]);

  // Precio EN VIVO: actualiza la última vela cada pocos segundos (Finnhub).
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const { price, realtime } = await api.price(symbol);
        if (cancelled) return;
        setRealtime(realtime);
        if (price == null) return;
        setRtPrice(price);
        const last = lastCandleRef.current;
        const candle = candleRef.current;
        if (last && candle) {
          const updated = {
            time: last.time,
            open: last.open,
            high: Math.max(last.high, price),
            low: Math.min(last.low, price),
            close: price,
          };
          lastCandleRef.current = updated;
          candle.update(updated as any);
        }
      } catch {
        /* ignora */
      }
    };
    tick();
    const id = setInterval(tick, 6000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [symbol, bundle]);

  const selectCls =
    "rounded-md border border-[var(--color-line)] bg-[var(--color-panel-2)] px-2 py-1 text-xs text-[var(--color-ink)] outline-none";

  return (
    <div>
      {/* Barra superior */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {/* Intervalo del gráfico */}
        <select
          value={interval}
          onChange={(e) => pickInterval(e.target.value)}
          className={selectCls}
          title="Intervalo del gráfico"
        >
          {INTERVALS.map((iv) => (
            <option key={iv.key} value={iv.key}>
              {iv.label}
            </option>
          ))}
        </select>

        {/* EMAs (panel desplegable) */}
        <div className="relative">
          <button
            onClick={() => setEmaPanel((v) => !v)}
            className={`rounded-md border border-[var(--color-line)] px-2 py-1 text-xs ${
              emaPanel
                ? "bg-[var(--color-accent)] text-white"
                : "bg-[var(--color-panel-2)] text-[var(--color-muted)] hover:text-white"
            }`}
          >
            ⚙ EMAs
          </button>
          {emaPanel && (
            <EmaSettings
              emas={emas}
              interval={interval}
              labels={tt}
              editEma={editEma}
              addEma={addEma}
              removeEma={removeEma}
            />
          )}
        </div>

        {/* Otros indicadores */}
        {(
          [
            ["volume", tt.volume],
            ["bollinger", "Bollinger"],
            ["levels", "S/R"],
            ["rsi", "RSI"],
            ["trendlines", tt.trendlines],
          ] as [keyof Opts, string][]
        ).map(([k, label]) => (
          <label key={k} className="flex cursor-pointer items-center gap-1 text-xs">
            <input type="checkbox" checked={opts[k]} onChange={() => toggleOpt(k)} />
            {label}
          </label>
        ))}

        <button
          onClick={() => setReloadKey((k) => k + 1)}
          title={tt.refreshTitle}
          className="ml-auto rounded-md border border-[var(--color-line)] bg-[var(--color-panel-2)] px-2 py-1 text-xs text-[var(--color-muted)] hover:text-white"
        >
          {loading ? "⏳" : "🔄"} {tt.refresh}
        </button>
        <span className="text-xs text-[var(--color-muted)]">
          {rtPrice != null && (
            <>
              {realtime ? "⚡" : "•"} {rtPrice}
            </>
          )}
        </span>
      </div>

      <div className="relative">
        <div
          ref={boxRef}
          className="h-[440px] w-full overflow-hidden rounded-xl border border-[var(--color-line)]"
        />
        {/* Horario regular vs extendido (esquina inferior derecha). Solo tiene
            efecto en intradía; fuera de intradía se muestra deshabilitado. */}
        <div
          className="absolute bottom-2 right-2 z-10 flex overflow-hidden rounded-md border border-[var(--color-line)] bg-[var(--color-panel)]/90 text-[10px] backdrop-blur"
          title={showSession ? tt.sessionTitleOn : tt.sessionTitleOff}
        >
          {(
            [
              ["regular", tt.regular],
              ["extended", tt.extended],
            ] as ["regular" | "extended", string][]
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => pickSession(key)}
              disabled={!showSession}
              className={`px-2 py-0.5 ${
                session === key && showSession
                  ? "bg-[var(--color-accent)] text-white"
                  : "text-[var(--color-muted)] hover:text-white"
              } ${!showSession ? "cursor-not-allowed opacity-50 hover:text-[var(--color-muted)]" : ""}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {opts.rsi && (
        <div
          ref={rsiBoxRef}
          className="mt-1 h-[110px] w-full overflow-hidden rounded-xl border border-[var(--color-line)]"
        />
      )}

      {/* Rangos: se atenúan los no permitidos por el intervalo */}
      <div className="mt-2 flex flex-wrap gap-1">
        {RANGES.map((r) => {
          const disabled = !okRanges.includes(r.key);
          const active = r.key === effRange;
          return (
            <button
              key={r.key}
              disabled={disabled}
              onClick={() => pickRange(r.key)}
              className={`rounded-md px-2 py-0.5 text-xs ${
                active
                  ? "bg-[var(--color-accent)] text-white"
                  : disabled
                    ? "cursor-not-allowed bg-[var(--color-panel-2)] text-[var(--color-line)]"
                    : "bg-[var(--color-panel-2)] text-[var(--color-muted)] hover:text-white"
              }`}
            >
              {r.key}
            </button>
          );
        })}
      </div>
    </div>
  );
}
