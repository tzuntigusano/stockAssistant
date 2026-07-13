/** Constantes y piezas de UI compartidas del radar/screener. */

export const CFG_KEY = "sa_radar_config";

import type { Lang } from "../../i18n";

export const PARAM_LABELS: Record<Lang, Record<string, string>> = {
  es: {
    donchian_n: "Máximo de N sesiones",
    vol_mult: "Volumen mín. (×media)",
    vol_window: "Ventana de volumen",
    rsi_thr: "RSI mínimo",
    adx_thr: "ADX mínimo",
    near_high_pct: "Cercanía a máx. 52s (%)",
    atr_min_pct: "Volatilidad mín. ATR (%)",
    rel_lookback: "Sesiones fuerza relativa",
    min_price: "Precio mínimo",
  },
  en: {
    donchian_n: "N-session high",
    vol_mult: "Min. volume (×avg)",
    vol_window: "Volume window",
    rsi_thr: "Min. RSI",
    adx_thr: "Min. ADX",
    near_high_pct: "Near 52w high (%)",
    atr_min_pct: "Min. volatility ATR (%)",
    rel_lookback: "Rel. strength sessions",
    min_price: "Min. price",
  },
};

export const WEIGHT_LABELS: Record<Lang, Record<string, string>> = {
  es: {
    donchian: "Rompimiento (Donchian)",
    volume: "Volumen alto",
    rsi: "RSI fuerte",
    macd: "MACD alcista",
    adx: "Fuerza de tendencia (ADX)",
    ema: "Sobre EMAs",
    high52: "Cerca de máx. 52s",
    rel_strength: "Fuerza relativa vs índice",
    obv: "OBV (acumulación)",
    bollinger: "Ruptura de Bollinger",
  },
  en: {
    donchian: "Breakout (Donchian)",
    volume: "High volume",
    rsi: "Strong RSI",
    macd: "Bullish MACD",
    adx: "Trend strength (ADX)",
    ema: "Above EMAs",
    high52: "Near 52w high",
    rel_strength: "Rel. strength vs index",
    obv: "OBV (accumulation)",
    bollinger: "Bollinger breakout",
  },
};

export function scoreColor(s: number) {
  return s >= 75 ? "var(--color-bull)" : s >= 50 ? "#f59e0b" : "var(--color-muted)";
}

export function NumField({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <div>
      <label className="stat-label">{label}</label>
      <input
        type="number"
        step={step}
        className="input mt-1"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  );
}
