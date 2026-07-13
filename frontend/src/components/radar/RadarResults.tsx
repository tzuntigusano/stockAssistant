import type { RadarResult } from "../../types";
import { fmtMoney, fmtPct, signColor, stockHref } from "../../helpers";
import { scoreColor } from "./radarUi";
import { useLang } from "../../i18n";

const T = {
  es: {
    results: "Resultados",
    scanned: "escaneados",
    match: "coinciden",
    empty:
      "Ningún valor supera la puntuación mínima con estos ajustes. Prueba a bajar la puntuación mínima o cambiar las fuentes.",
    price: "Precio",
    unwatch: "Quitar de seguimiento",
    watch: "Seguir",
    watching: "★ Siguiendo",
    watchBtn: "☆ Seguir",
    disclaimer:
      "Pulsa cualquier valor para abrir su análisis completo. Señala configuraciones técnicas favorables, no valores que vayan a subir con seguridad. No es asesoramiento financiero.",
  },
  en: {
    results: "Results",
    scanned: "scanned",
    match: "match",
    empty:
      "No stock beats the min. score with these settings. Try lowering the min. score or changing the sources.",
    price: "Price",
    unwatch: "Unwatch",
    watch: "Watch",
    watching: "★ Watching",
    watchBtn: "☆ Watch",
    disclaimer:
      "Click any stock to open its full analysis. It flags favorable technical setups, not stocks that will surely go up. Not financial advice.",
  },
} as const;

export default function RadarResults({
  result,
  watched,
  onOpen,
  onToggleWatch,
}: {
  result: RadarResult;
  watched: Set<string>;
  onOpen: (e: React.MouseEvent, sym: string) => void;
  onToggleWatch: (e: React.MouseEvent, sym: string) => void;
}) {
  const t = T[useLang()];
  return (
    <div className="card">
      <div className="card-title">
        <span>{t.results}</span>
        <span className="ml-auto text-xs font-normal normal-case text-[var(--color-muted)]">
          {result.scanned} {t.scanned} · {result.matched} {t.match} · {result.benchmark}{" "}
          {fmtPct(result.benchmark_return)}
        </span>
      </div>

      {result.candidates.length === 0 ? (
        <p className="text-sm text-[var(--color-muted)]">{t.empty}</p>
      ) : (
        <div className="space-y-2">
          {result.candidates.map((c) => (
            <div
              key={c.ticker}
              className="flex w-full flex-col gap-2 rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] p-3 transition hover:border-[var(--color-accent)] sm:flex-row sm:items-center"
            >
              <a
                href={stockHref(c.ticker)}
                onClick={(e) => onOpen(e, c.ticker)}
                className="flex flex-1 cursor-pointer flex-col gap-2 text-left sm:flex-row sm:items-center"
              >
                <div className="flex w-14 shrink-0 flex-col items-center">
                  <span
                    className="text-2xl font-bold tabular-nums"
                    style={{ color: scoreColor(c.score) }}
                  >
                    {c.score}
                  </span>
                  <span className="text-[10px] text-[var(--color-muted)]">/ 100</span>
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="font-semibold text-[var(--color-accent)]">{c.ticker}</span>
                    <span className="truncate text-xs text-[var(--color-muted)]">{c.name}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {c.passed.map((p, i) => (
                      <span
                        key={i}
                        className="rounded bg-[var(--color-bull)]/12 px-1.5 py-0.5 text-[11px] text-[var(--color-bull)]"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex shrink-0 gap-4 text-right text-xs">
                  <div>
                    <div className="stat-label">{t.price}</div>
                    <div className="stat-value">{fmtMoney(c.price, "USD")}</div>
                    <div className={signColor(c.change_pct)}>{fmtPct(c.change_pct)}</div>
                  </div>
                  <div>
                    <div className="stat-label">RSI / ADX</div>
                    <div className="stat-value">
                      {c.rsi ?? "—"} / {c.adx ?? "—"}
                    </div>
                    <div className="text-[var(--color-muted)]">
                      vol {c.vol_ratio ? `${c.vol_ratio}×` : "—"}
                    </div>
                  </div>
                </div>
              </a>

              <button
                onClick={(e) => onToggleWatch(e, c.ticker)}
                className={`shrink-0 rounded-lg border px-2.5 py-1.5 text-xs transition ${
                  watched.has(c.ticker)
                    ? "border-[var(--color-bull)] text-[var(--color-bull)]"
                    : "border-[var(--color-line)] text-[var(--color-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-ink)]"
                }`}
                title={watched.has(c.ticker) ? t.unwatch : t.watch}
              >
                {watched.has(c.ticker) ? t.watching : t.watchBtn}
              </button>
            </div>
          ))}
        </div>
      )}
      <p className="mt-4 border-t border-[var(--color-line)] pt-3 text-xs text-[var(--color-muted)]">
        {t.disclaimer}
      </p>
    </div>
  );
}
