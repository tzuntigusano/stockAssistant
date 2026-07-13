import { useEffect, useState } from "react";
import { api } from "../api";
import type { BreakoutScore } from "../types";
import { useLang } from "../i18n";

const T = {
  es: {
    title: "🚀 Señales de rompimiento (radar)",
    evaluating: "Evaluando señales…",
    noData: "No hay datos suficientes para evaluar el rompimiento de este valor.",
    meetsA: "Cumple",
    meetsB: "de",
    meetsC:
      "señales de rompimiento alcista (misma lógica que el Radar, aplicada solo a este valor).",
    disclaimer:
      "Señala una configuración técnica favorable, no una predicción. No es asesoramiento financiero.",
  },
  en: {
    title: "🚀 Breakout signals (radar)",
    evaluating: "Evaluating signals…",
    noData: "Not enough data to evaluate a breakout for this stock.",
    meetsA: "Meets",
    meetsB: "of",
    meetsC: "bullish breakout signals (same logic as the Radar, applied to this stock only).",
    disclaimer: "It flags a favorable technical setup, not a prediction. Not financial advice.",
  },
} as const;

function scoreColor(s: number) {
  return s >= 75 ? "var(--color-bull)" : s >= 50 ? "#f59e0b" : "var(--color-muted)";
}

export default function BreakoutPanel({ ticker }: { ticker: string }) {
  const lang = useLang();
  const t = T[lang];
  const [data, setData] = useState<BreakoutScore | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setData(null);
    api
      .radarScoreOne(ticker)
      .then((d) => !cancelled && setData(d))
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [ticker, lang]);

  const passed = data?.checklist?.filter((c) => c.passed).length ?? 0;
  const total = data?.checklist?.length ?? 0;

  return (
    <div className="card">
      <div className="card-title">
        <span>{t.title}</span>
        {data?.ok && data.score !== undefined && (
          <span
            className="ml-auto text-2xl font-bold tabular-nums"
            style={{ color: scoreColor(data.score) }}
          >
            {data.score}
            <span className="text-xs font-normal text-[var(--color-muted)]"> / 100</span>
          </span>
        )}
      </div>

      {loading && <p className="text-sm text-[var(--color-muted)]">{t.evaluating}</p>}

      {!loading && !data?.ok && <p className="text-sm text-[var(--color-muted)]">{t.noData}</p>}

      {data?.ok && data.checklist && (
        <>
          <p className="mb-3 text-sm text-[var(--color-muted)]">
            {t.meetsA}{" "}
            <strong className="text-[var(--color-ink)]">
              {passed} {t.meetsB} {total}
            </strong>{" "}
            {t.meetsC}
          </p>
          <ul className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
            {data.checklist.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span
                  className={c.passed ? "text-[var(--color-bull)]" : "text-[var(--color-muted)]"}
                >
                  {c.passed ? "✓" : "✗"}
                </span>
                <span
                  className={
                    c.passed
                      ? "text-[var(--color-ink)]/90"
                      : "text-[var(--color-muted)] line-through"
                  }
                >
                  {c.label}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-4 border-t border-[var(--color-line)] pt-3 text-xs text-[var(--color-muted)]">
            {t.disclaimer}
          </p>
        </>
      )}
    </div>
  );
}
