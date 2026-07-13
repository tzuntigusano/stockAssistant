import type { Quote } from "../types";
import { fmtCompact, fmtMoney, fmtNum, fmtPct, signColor } from "../helpers";
import { useLang } from "../i18n";

const T = {
  es: {
    open: "Apertura",
    high: "Máx. día",
    low: "Mín. día",
    prevClose: "Cierre ant.",
    range52: "Rango 52 sem.",
    mcap: "Capitalización",
    pe: "PER",
    divYield: "Rentab. div.",
    sector: "Sector",
  },
  en: {
    open: "Open",
    high: "Day high",
    low: "Day low",
    prevClose: "Prev. close",
    range52: "52w range",
    mcap: "Market cap",
    pe: "P/E",
    divYield: "Div. yield",
    sector: "Sector",
  },
} as const;

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

export default function QuoteHeader({ quote }: { quote: Quote }) {
  const cur = quote.currency;
  const t = T[useLang()];
  return (
    <div className="card">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[var(--color-muted)]">
            <span className="text-sm font-semibold text-[var(--color-ink)]">{quote.symbol}</span>
            {quote.exchange && (
              <span className="rounded bg-[var(--color-panel-2)] px-1.5 py-0.5 text-xs">
                {quote.exchange}
              </span>
            )}
          </div>
          <h1 className="mt-0.5 text-lg font-medium">{quote.name}</h1>
        </div>
        <div className="text-right">
          <div className="text-3xl font-semibold tabular-nums">{fmtMoney(quote.price, cur)}</div>
          <div className={`text-sm font-medium ${signColor(quote.change)}`}>
            {quote.change !== undefined ? fmtMoney(quote.change, cur) : "—"} (
            {fmtPct(quote.change_pct)})
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 border-t border-[var(--color-line)] pt-4 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label={t.open} value={fmtMoney(quote.open, cur)} />
        <Stat label={t.high} value={fmtMoney(quote.day_high, cur)} />
        <Stat label={t.low} value={fmtMoney(quote.day_low, cur)} />
        <Stat label={t.prevClose} value={fmtMoney(quote.previous_close, cur)} />
        <Stat
          label={t.range52}
          value={`${fmtNum(quote.fifty_two_low)} – ${fmtNum(quote.fifty_two_high)}`}
        />
        <Stat label={t.mcap} value={fmtCompact(quote.market_cap)} />
        <Stat label={t.pe} value={fmtNum(quote.pe_ratio)} />
        <Stat
          label={t.divYield}
          value={quote.dividend_yield ? fmtPct(quote.dividend_yield) : "—"}
        />
        {quote.sector && <Stat label={t.sector} value={quote.sector} />}
      </div>
    </div>
  );
}
