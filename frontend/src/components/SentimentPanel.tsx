import { useState } from "react";
import type { Sentiment, Verdict } from "../types";
import { useLang } from "../i18n";

const T = {
  es: {
    title: "📊 Sentimiento técnico",
    of100: "de 100",
    tabs: { "1h": "1 hora", "4h": "4 horas", "1d": "Diario" },
    noSignals: "Sin señales suficientes en esta temporalidad.",
    disclaimer:
      "Veredicto por reglas técnicas deterministas (RSI, EMAs, MACD, tendencia) en cada temporalidad. No es asesoramiento financiero.",
  },
  en: {
    title: "📊 Technical sentiment",
    of100: "of 100",
    tabs: { "1h": "1 hour", "4h": "4 hours", "1d": "Daily" },
    noSignals: "Not enough signals in this timeframe.",
    disclaimer:
      "Verdict from deterministic technical rules (RSI, EMAs, MACD, trend) per timeframe. Not financial advice.",
  },
} as const;

// El veredicto llega del backend en español; lo mapeamos al idioma elegido.
const VERDICT_EN: Record<string, string> = {
  "MUY ALCISTA": "VERY BULLISH",
  ALCISTA: "BULLISH",
  NEUTRAL: "NEUTRAL",
  BAJISTA: "BEARISH",
  "MUY BAJISTA": "VERY BEARISH",
};

function colorFor(score: number) {
  return score >= 58 ? "var(--color-bull)" : score > 42 ? "#f59e0b" : "var(--color-bear)";
}

/** Medidor semicircular 0-100 (rojo → ámbar → verde). */
function Gauge({ score }: { score: number }) {
  const angle = (score / 100) * 180 - 90;
  const color = colorFor(score);
  return (
    <div className="relative mx-auto w-48">
      <svg viewBox="0 0 200 110" className="w-full">
        <path
          d="M 10 100 A 90 90 0 0 1 190 100"
          fill="none"
          stroke="var(--color-line)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d="M 10 100 A 90 90 0 0 1 190 100"
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${(score / 100) * 283} 283`}
        />
        <line
          x1="100"
          y1="100"
          x2={100 + 70 * Math.cos((angle - 90) * (Math.PI / 180))}
          y2={100 + 70 * Math.sin((angle - 90) * (Math.PI / 180))}
          stroke="var(--color-ink)"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="100" cy="100" r="5" fill="var(--color-ink)" />
      </svg>
      <div className="-mt-6 text-center">
        <div className="text-3xl font-bold tabular-nums" style={{ color }}>
          {score}
        </div>
        <div className="text-xs text-[var(--color-muted)]">{T[useLang()].of100}</div>
      </div>
    </div>
  );
}

const TAB_KEYS: (keyof Sentiment)[] = ["1h", "4h", "1d"];

export default function SentimentPanel({
  sentiment,
  fallback,
}: {
  sentiment: Sentiment | null;
  fallback: Verdict;
}) {
  const lang = useLang();
  const t = T[lang];
  const [tab, setTab] = useState<keyof Sentiment>("1d");

  // Mientras carga el multi-timeframe usamos el veredicto diario del análisis.
  const verdict: Verdict = sentiment ? sentiment[tab].verdict : fallback;
  const color = colorFor(verdict.score);
  const verdictLabel = lang === "en" ? (VERDICT_EN[verdict.label] ?? verdict.label) : verdict.label;

  return (
    <div className="card">
      <div className="card-title">{t.title}</div>

      {/* Pestañas de temporalidad */}
      <div className="mb-4 flex gap-1 rounded-lg bg-[var(--color-panel-2)] p-1">
        {TAB_KEYS.map((key) => {
          const s = sentiment?.[key].verdict.score;
          const active = tab === key;
          return (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition ${
                active
                  ? "bg-[var(--color-accent)] text-white"
                  : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
              }`}
            >
              {t.tabs[key]}
              {s !== undefined && (
                <span
                  className="ml-1 tabular-nums"
                  style={{ color: active ? "white" : colorFor(s) }}
                >
                  {s}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <Gauge score={verdict.score} />
      <div className="mt-2 text-center text-lg font-bold tracking-wide" style={{ color }}>
        {verdictLabel}
      </div>

      <div className="mt-5 space-y-2">
        {verdict.signals.length === 0 && (
          <p className="text-sm text-[var(--color-muted)]">{t.noSignals}</p>
        )}
        {verdict.signals.map((s, i) => (
          <div key={i} className="flex items-start gap-2 text-sm">
            <span
              className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
              style={{
                background: s.bias === "alcista" ? "var(--color-bull)" : "var(--color-bear)",
              }}
            />
            <span className="text-[var(--color-ink)]/90">{s.text}</span>
          </div>
        ))}
      </div>
      <p className="mt-4 border-t border-[var(--color-line)] pt-3 text-xs text-[var(--color-muted)]">
        {t.disclaimer}
      </p>
    </div>
  );
}
