import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { Analysis, Position, Sentiment } from "../types";
import QuoteHeader from "../components/QuoteHeader";
import TradingViewChart from "../components/TradingViewChart";
import LiveChart from "../components/LiveChart";
import SentimentPanel from "../components/SentimentPanel";
import BreakoutPanel from "../components/BreakoutPanel";
import StrategyChat from "../components/StrategyChat";
import LotsPanel from "../components/LotsPanel";
import AlertsPanel from "../components/AlertsPanel";
import SetupAlertsPanel from "../components/SetupAlertsPanel";
import FeedPanel from "../components/FeedPanel";
import WatchButton from "../components/WatchButton";
import RadarToggle from "../components/RadarToggle";
import DataLoadingBanner from "../components/DataLoadingBanner";
import { useLang } from "../i18n";

export default function StockView({
  ticker,
  llmAvailable,
}: {
  ticker: string;
  llmAvailable: boolean;
}) {
  const lang = useLang();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [sentiment, setSentiment] = useState<Sentiment | null>(null);
  const [position, setPosition] = useState<Position | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartMode, setChartMode] = useState<"tv" | "live">(
    () => (localStorage.getItem("sa_chart_mode") as "tv" | "live") || "tv"
  );

  const pickChart = (m: "tv" | "live") => {
    setChartMode(m);
    localStorage.setItem("sa_chart_mode", m);
  };

  const loadPosition = useCallback(async () => {
    try {
      setPosition(await api.lots(ticker));
    } catch {
      /* ignora */
    }
  }, [ticker]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setAnalysis(null);
    setSentiment(null);
    (async () => {
      try {
        const a = await api.analysis(ticker);
        if (!cancelled) setAnalysis(a);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    loadPosition();
    api
      .sentiment(ticker)
      .then((s) => !cancelled && setSentiment(s))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // `lang`: recarga análisis/sentimiento al cambiar de idioma (textos del backend).
  }, [ticker, loadPosition, lang]);

  if (loading) {
    return (
      <div className="space-y-4">
        <DataLoadingBanner />
        <div className="flex h-64 items-center justify-center text-[var(--color-muted)]">
          {lang === "en" ? "Loading" : "Cargando"} {ticker}…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card mt-4 text-center">
        <p className="text-[var(--color-bear)]">
          {lang === "en" ? `Couldn't load "${ticker}".` : `No se pudo cargar «${ticker}».`}
        </p>
        <p className="mt-1 text-sm text-[var(--color-muted)]">{error}</p>
      </div>
    );
  }

  if (!analysis) return null;
  const currency = analysis.quote.currency;

  return (
    <div className="space-y-4">
      <DataLoadingBanner />
      <div className="flex flex-wrap justify-end gap-2">
        <RadarToggle ticker={ticker} />
        <WatchButton ticker={ticker} />
      </div>

      <QuoteHeader quote={analysis.quote} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-2 flex gap-1 text-xs">
            <button
              onClick={() => pickChart("tv")}
              className={`rounded-md px-2.5 py-1 ${
                chartMode === "tv"
                  ? "bg-[var(--color-accent)] text-black"
                  : "bg-[var(--color-panel)] text-[var(--color-muted)] hover:text-white"
              }`}
            >
              TradingView
            </button>
            <button
              onClick={() => pickChart("live")}
              className={`rounded-md px-2.5 py-1 ${
                chartMode === "live"
                  ? "bg-[var(--color-accent)] text-black"
                  : "bg-[var(--color-panel)] text-[var(--color-muted)] hover:text-white"
              }`}
            >
              {lang === "en" ? "Live ⚡" : "En vivo ⚡"}
            </button>
          </div>
          {chartMode === "tv" ? (
            <TradingViewChart symbol={ticker} />
          ) : (
            <LiveChart symbol={ticker} />
          )}
        </div>
        <SentimentPanel sentiment={sentiment} fallback={analysis.verdict} />
      </div>

      <BreakoutPanel ticker={ticker} />

      <StrategyChat ticker={ticker} currency={currency} hasPosition={!!position?.has_position} />

      <LotsPanel ticker={ticker} position={position} currency={currency} onChange={loadPosition} />

      <SetupAlertsPanel ticker={ticker} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <AlertsPanel ticker={ticker} />
        <FeedPanel ticker={ticker} />
      </div>
    </div>
  );
}
