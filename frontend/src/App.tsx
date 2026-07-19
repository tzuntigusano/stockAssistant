import { useEffect, useState } from "react";
import { api } from "./api";
import { useStore } from "./store/useStore";
import { useLang } from "./i18n";
import SearchBar from "./components/SearchBar";
import StockView from "./pages/StockView";
import Dashboard from "./components/Dashboard";
import Radar from "./components/Radar";
import AlertsBell from "./components/AlertsBell";
import AlertsView from "./components/AlertsView";
import PaperView from "./components/PaperView";
import RestartButton from "./components/RestartButton";

const T = {
  es: {
    home: "Inicio",
    analyzer: "Analizador",
    radar: "Radar",
    portfolio: "Cartera",
    alerts: "Alertas",
    alertsTitle: "Mis alertas (ver y desactivar)",
    paper: "Ficticias",
    paperTitle: "Carteras ficticias (dinero simulado)",
    radarTitle: "Radar de oportunidades",
    backTo: "Volver a",
    aiPrefix: "IA",
    aiOff: "IA off",
    footer:
      "Uso personal · Datos de Yahoo Finance · Gráficos de TradingView · IA por Gemini. Esto es información, no asesoramiento financiero.",
  },
  en: {
    home: "Home",
    analyzer: "Analyzer",
    radar: "Radar",
    portfolio: "Portfolio",
    alerts: "Alerts",
    alertsTitle: "My alerts (view and pause)",
    paper: "Paper",
    paperTitle: "Paper portfolios (simulated money)",
    radarTitle: "Opportunities radar",
    backTo: "Back to",
    aiPrefix: "AI",
    aiOff: "AI off",
    footer:
      "Personal use · Yahoo Finance data · TradingView charts · AI by Gemini. This is information, not financial advice.",
  },
} as const;

export default function App() {
  const ticker = useStore((s) => s.ticker);
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);
  const goHome = useStore((s) => s.goHome);
  const goBack = useStore((s) => s.goBack);
  const history = useStore((s) => s.history);
  const lang = useLang();
  const setLang = useStore((s) => s.setLang);
  const t = T[lang];
  const [llm, setLlm] = useState<{ available: boolean; model: string } | null>(null);

  const prev = history.length > 0 ? history[history.length - 1] : null;
  const backLabel = prev
    ? prev.ticker
      ? prev.ticker
      : prev.view === "radar"
        ? t.radar
        : prev.view === "alerts"
          ? t.alerts
          : prev.view === "paper"
            ? t.paper
            : t.portfolio
    : "";

  useEffect(() => {
    api
      .llmStatus()
      .then(setLlm)
      .catch(() => setLlm({ available: false, model: "" }));
  }, []);

  // Al cargar, si la URL trae ?stock=TICKER (pestaña nueva), abre esa ficha.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const stock = params.get("stock");
    if (stock) {
      useStore.getState().setTicker(stock);
    } else {
      const v = params.get("view");
      if (v === "radar" || v === "alerts" || v === "paper") {
        useStore.getState().setView(v);
      }
    }
  }, []);

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-[var(--color-line)] bg-[var(--color-bg)]/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          {prev && (
            <button
              onClick={goBack}
              className="shrink-0 rounded-lg border border-[var(--color-line)] px-2.5 py-1.5 text-sm text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-ink)]"
              title={`${t.backTo} ${backLabel}`}
            >
              ← <span className="hidden sm:inline">{backLabel}</span>
            </button>
          )}
          <button onClick={goHome} className="shrink-0 text-lg font-bold" title={t.home}>
            📈 <span className="hidden sm:inline">{t.analyzer}</span>
          </button>
          <SearchBar />
          <button
            onClick={() => setView("radar")}
            className={`shrink-0 rounded-lg px-2.5 py-1.5 text-sm transition ${
              !ticker && view === "radar"
                ? "bg-[var(--color-accent)] text-white"
                : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
            }`}
            title={t.radarTitle}
          >
            🔎 <span className="hidden sm:inline">{t.radar}</span>
          </button>
          <button
            onClick={() => setView("alerts")}
            className={`shrink-0 rounded-lg px-2.5 py-1.5 text-sm transition ${
              !ticker && view === "alerts"
                ? "bg-[var(--color-accent)] text-white"
                : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
            }`}
            title={t.alertsTitle}
          >
            🔔 <span className="hidden sm:inline">{t.alerts}</span>
          </button>
          <button
            onClick={() => setView("paper")}
            className={`shrink-0 rounded-lg px-2.5 py-1.5 text-sm transition ${
              !ticker && view === "paper"
                ? "bg-[var(--color-accent)] text-white"
                : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
            }`}
            title={t.paperTitle}
          >
            🧪 <span className="hidden sm:inline">{t.paper}</span>
          </button>
          <div className="ml-auto flex items-center gap-3">
            {/* Selector de idioma */}
            <div className="flex overflow-hidden rounded-lg border border-[var(--color-line)] text-xs">
              {(["es", "en"] as const).map((l) => (
                <button
                  key={l}
                  onClick={() => setLang(l)}
                  className={`px-2 py-1 ${
                    lang === l
                      ? "bg-[var(--color-accent)] text-white"
                      : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
                  }`}
                >
                  {l.toUpperCase()}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
              <span
                className={`h-2 w-2 rounded-full ${
                  llm?.available ? "bg-[var(--color-bull)]" : "bg-[var(--color-bear)]"
                }`}
              />
              <span className="hidden sm:inline">
                {llm?.available ? `${t.aiPrefix}: ${llm.model}` : t.aiOff}
              </span>
            </div>
            <RestartButton />
            <AlertsBell />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {ticker ? (
          <StockView ticker={ticker} llmAvailable={!!llm?.available} />
        ) : view === "radar" ? (
          <Radar />
        ) : view === "alerts" ? (
          <AlertsView />
        ) : view === "paper" ? (
          <PaperView />
        ) : (
          <Dashboard />
        )}
      </main>

      <footer className="mx-auto max-w-6xl px-4 py-8 text-center text-xs text-[var(--color-muted)]">
        {t.footer}
      </footer>
    </div>
  );
}
