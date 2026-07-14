// Constantes, tipos y helpers puros del LiveChart.
// Separados del componente para que las ediciones frecuentes de estilo/rango
// no obliguen a leer todo el componente (y viceversa).

export type Ema = { id: number; on: boolean; length: number; tf: string; color: string };
export type Opts = {
  volume: boolean;
  bollinger: boolean;
  levels: boolean;
  rsi: boolean;
  trendlines: boolean;
};

export const EMA_PALETTE = ["#06b6d4", "#3b82f6", "#f59e0b", "#a855f7", "#ec4899", "#10b981"];

// Colores del gráfico (no son variables CSS porque lightweight-charts los pide en JS).
export const C = {
  bg: "#111722",
  grid: "#232c3d",
  text: "#8b98a9",
  bull: "#22c55e",
  bear: "#ef4444",
  bb: "rgba(139,152,169,0.5)",
};

// Intervalos del gráfico (etiqueta ↔ token que entiende el backend).
export const INTERVALS: { key: string; label: string }[] = [
  { key: "5m", label: "5m" },
  { key: "15m", label: "15m" },
  { key: "60m", label: "1h" },
  { key: "4h", label: "4h" },
  { key: "1d", label: "1D" },
  { key: "1wk", label: "1S" },
];

// Timeframes que puede tener una EMA (MTF). "" = mismo que el gráfico.
export const TF_OPTS: { key: string; label: string; rank: number }[] = [
  { key: "1h", label: "1h", rank: 3 },
  { key: "4h", label: "4h", rank: 4 },
  { key: "1d", label: "1D", rank: 5 },
  { key: "1wk", label: "1S", rank: 6 },
];
export const RANK: Record<string, number> = {
  "5m": 1,
  "15m": 2,
  "60m": 3,
  "4h": 4,
  "1d": 5,
  "1wk": 6,
};

// Rangos (periodo de histórico) y su equivalente para el backend.
export const RANGES: { key: string; period: string }[] = [
  { key: "1D", period: "1d" },
  { key: "5D", period: "5d" },
  { key: "1M", period: "1mo" },
  { key: "3M", period: "3mo" },
  { key: "6M", period: "6mo" },
  { key: "1A", period: "1y" },
  { key: "5A", period: "5y" },
  { key: "Máx", period: "max" },
];

// Rangos válidos por intervalo: ni tan largo que no haya datos, ni tan corto
// que salgan 1-2 velas (p.ej. diario+1D = 1 vela → gráfico roto).
export function allowedRanges(interval: string): string[] {
  switch (interval) {
    case "5m":
    case "15m":
      return ["1D", "5D", "1M"];
    case "60m":
      return ["5D", "1M", "3M", "6M", "1A"];
    case "4h":
      return ["1M", "3M", "6M", "1A"];
    case "1wk":
      return ["6M", "1A", "5A", "Máx"];
    default: // 1d
      return ["1M", "3M", "6M", "1A", "5A", "Máx"];
  }
}

// Rango por defecto (buena cantidad de velas) al cambiar de intervalo.
export const DEFAULT_RANGE_FOR: Record<string, string> = {
  "5m": "5D",
  "15m": "1M",
  "60m": "1M",
  "4h": "3M",
  "1d": "1A",
  "1wk": "5A",
};

export const DEFAULT_EMAS: Ema[] = [
  { id: 1, on: true, length: 9, tf: "", color: "#06b6d4" },
  { id: 2, on: true, length: 20, tf: "", color: "#3b82f6" },
  { id: 3, on: true, length: 50, tf: "", color: "#f59e0b" },
  { id: 4, on: false, length: 200, tf: "", color: "#a855f7" },
];

export const DEFAULT_OPTS: Opts = {
  volume: true,
  bollinger: false,
  levels: true,
  rsi: false,
  trendlines: false,
};

// Claves de localStorage.
export const K = {
  opts: "sa_chart_opts",
  emas: "sa_chart_emas",
  interval: "sa_chart_interval",
  range: "sa_chart_range",
  session: "sa_chart_session",
};

// El horario extendido (pre/after market) solo cambia los datos en intradía.
export const INTRADAY = new Set(["5m", "15m", "60m", "4h"]);

export function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? { ...(fallback as any), ...JSON.parse(raw) } : fallback;
  } catch {
    return fallback;
  }
}
