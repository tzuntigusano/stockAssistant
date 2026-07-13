import { useEffect, useState } from "react";
import { api } from "../api";
import type { Portfolio, WatchlistItem } from "../types";
import { useStore } from "../store/useStore";
import { fmtMoney, fmtNum, fmtPct, signColor, stockHref } from "../helpers";
import { useLang } from "../i18n";

const TX = {
  es: {
    title: "Mi cartera",
    subtitle: "Busca un valor arriba o pulsa cualquiera para abrir su análisis.",
    loading: "Cargando cartera…",
    marketValue: "Valor de mercado",
    unrealized: "P&L no realizado",
    realized: "P&L realizado",
    invested: "Coste invertido",
    holdings: "📁 Valores",
    thStock: "Valor",
    thPrice: "Precio",
    thDay: "Día",
    thShares: "Acciones",
    thValue: "Valor",
    thPnl: "P&L no real.",
    closed: "cerrado · real.",
    watchlist: "⭐ Seguimiento",
    liveMon: "🚀 Monitoreo en directo",
    liveSub: "vigilados cada ~45 s en busca de rupturas",
    empty:
      "Aún no tienes valores. Registra compras en la página de una acción o añádela a seguimiento para verla aquí.",
    recent: "Recientes",
    popular: "Populares",
  },
  en: {
    title: "My portfolio",
    subtitle: "Search a stock above or click any to open its analysis.",
    loading: "Loading portfolio…",
    marketValue: "Market value",
    unrealized: "Unrealized P&L",
    realized: "Realized P&L",
    invested: "Invested cost",
    holdings: "📁 Holdings",
    thStock: "Stock",
    thPrice: "Price",
    thDay: "Day",
    thShares: "Shares",
    thValue: "Value",
    thPnl: "Unreal. P&L",
    closed: "closed · real.",
    watchlist: "⭐ Watchlist",
    liveMon: "🚀 Live monitoring",
    liveSub: "watched every ~45 s for breakouts",
    empty:
      "You don't have any stocks yet. Record buys on a stock's page or add it to your watchlist to see it here.",
    recent: "Recent",
    popular: "Popular",
  },
} as const;

export default function Dashboard() {
  const L = TX[useLang()];
  const { setTicker, recents } = useStore();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watch, setWatch] = useState<WatchlistItem[]>([]);
  const [radar, setRadar] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.portfolio(), api.watchlist(), api.radarwatch()])
      .then(([p, w, r]) => {
        setPortfolio(p);
        setWatch(w);
        setRadar(r);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const populares = ["AAPL", "MSFT", "NVDA", "NOK", "TSLA", "AMZN"];
  const hasPortfolio = portfolio && portfolio.items.length > 0;
  const t = portfolio?.totals;

  function openStock(e: React.MouseEvent, sym: string) {
    // Deja pasar Ctrl/⌘/Shift para "abrir en pestaña nueva".
    if (e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    setTicker(sym);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{L.title}</h1>
        <p className="mt-1 text-sm text-[var(--color-muted)]">{L.subtitle}</p>
      </div>

      {loading && <p className="text-[var(--color-muted)]">{L.loading}</p>}

      {/* Totales de la cartera */}
      {hasPortfolio && t && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="card">
            <div className="stat-label">{L.marketValue}</div>
            <div className="mt-1 text-xl font-semibold">{fmtNum(t.market_value)}</div>
          </div>
          <div className="card">
            <div className="stat-label">{L.unrealized}</div>
            <div className={`mt-1 text-xl font-semibold ${signColor(t.unrealized_pnl)}`}>
              {fmtNum(t.unrealized_pnl)}
            </div>
            <div className={`text-xs ${signColor(t.unrealized_pnl)}`}>
              {fmtPct(t.unrealized_pnl_pct)}
            </div>
          </div>
          <div className="card">
            <div className="stat-label">{L.realized}</div>
            <div className={`mt-1 text-xl font-semibold ${signColor(t.realized_pnl)}`}>
              {fmtNum(t.realized_pnl)}
            </div>
          </div>
          <div className="card">
            <div className="stat-label">{L.invested}</div>
            <div className="mt-1 text-xl font-semibold">{fmtNum(t.cost)}</div>
          </div>
        </div>
      )}

      {/* Lista de valores en cartera */}
      {hasPortfolio && (
        <div className="card">
          <div className="card-title">{L.holdings}</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[var(--color-muted)]">
                  <th className="pb-2 font-medium">{L.thStock}</th>
                  <th className="pb-2 font-medium">{L.thPrice}</th>
                  <th className="pb-2 font-medium">{L.thDay}</th>
                  <th className="pb-2 font-medium">{L.thShares}</th>
                  <th className="pb-2 font-medium">{L.thValue}</th>
                  <th className="pb-2 font-medium">{L.thPnl}</th>
                </tr>
              </thead>
              <tbody>
                {portfolio!.items.map((it) => (
                  <tr
                    key={it.ticker}
                    onClick={() => setTicker(it.ticker)}
                    className="cursor-pointer border-t border-[var(--color-line)] transition hover:bg-[var(--color-panel-2)]"
                  >
                    <td className="py-2.5">
                      <div className="font-semibold text-[var(--color-accent)]">{it.ticker}</div>
                      <div className="truncate text-xs text-[var(--color-muted)]">{it.name}</div>
                    </td>
                    <td className="py-2.5">{fmtMoney(it.price, it.currency)}</td>
                    <td className={`py-2.5 ${signColor(it.change_pct)}`}>
                      {fmtPct(it.change_pct)}
                    </td>
                    <td className="py-2.5">{it.has_position ? fmtNum(it.shares, 2) : "—"}</td>
                    <td className="py-2.5">
                      {it.has_position ? fmtMoney(it.market_value, it.currency) : "—"}
                    </td>
                    <td className={`py-2.5 ${signColor(it.unrealized_pnl)}`}>
                      {it.has_position
                        ? `${fmtMoney(it.unrealized_pnl, it.currency)} (${fmtPct(it.unrealized_pnl_pct)})`
                        : it.realized_pnl
                          ? `${L.closed} ${fmtNum(it.realized_pnl)}`
                          : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Lista de seguimiento */}
      {watch.length > 0 && (
        <div className="card">
          <div className="card-title">{L.watchlist}</div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {watch.map((w) => (
              <a
                key={w.ticker}
                href={stockHref(w.ticker)}
                onClick={(e) => openStock(e, w.ticker)}
                className="block cursor-pointer rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] p-3 text-left transition hover:border-[var(--color-accent)]"
              >
                <div className="font-semibold">{w.ticker}</div>
                <div className="truncate text-xs text-[var(--color-muted)]">{w.name}</div>
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-sm">{fmtMoney(w.price, w.currency)}</span>
                  <span className={`text-xs ${signColor(w.change_pct)}`}>
                    {fmtPct(w.change_pct)}
                  </span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Monitoreo en directo (radar de rupturas) — lista separada */}
      {radar.length > 0 && (
        <div className="card">
          <div className="card-title">
            <span>{L.liveMon}</span>
            <span className="ml-auto text-xs font-normal normal-case text-[var(--color-muted)]">
              {L.liveSub}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {radar.map((w) => (
              <a
                key={w.ticker}
                href={stockHref(w.ticker)}
                onClick={(e) => openStock(e, w.ticker)}
                className="block cursor-pointer rounded-lg border border-[var(--color-bull)]/40 bg-[var(--color-panel-2)] p-3 text-left transition hover:border-[var(--color-bull)]"
              >
                <div className="font-semibold">🚀 {w.ticker}</div>
                <div className="truncate text-xs text-[var(--color-muted)]">{w.name}</div>
                <div className="mt-1 flex items-center justify-between">
                  <span className="text-sm">{fmtMoney(w.price, w.currency)}</span>
                  <span className={`text-xs ${signColor(w.change_pct)}`}>
                    {fmtPct(w.change_pct)}
                  </span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Vacío / accesos rápidos */}
      {!loading && !hasPortfolio && watch.length === 0 && (
        <p className="text-sm text-[var(--color-muted)]">{L.empty}</p>
      )}

      <div>
        <div className="stat-label mb-2">{recents.length > 0 ? L.recent : L.popular}</div>
        <div className="flex flex-wrap gap-2">
          {(recents.length > 0 ? recents : populares).map((r) => (
            <button key={r} className="btn-ghost" onClick={() => setTicker(r)}>
              {r}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
