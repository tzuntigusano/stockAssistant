import { useEffect, useState } from "react";
import { api } from "../api";
import type { RadarConfig, RadarSource } from "../types";
import { useStore } from "../store/useStore";
import { useLang } from "../i18n";
import RadarConfigPanel from "./radar/RadarConfigPanel";
import RadarResults from "./radar/RadarResults";
import { CFG_KEY } from "./radar/radarUi";

export default function Radar() {
  const lang = useLang();
  const setTicker = useStore((s) => s.setTicker);
  const result = useStore((s) => s.radarResult);
  const setResult = useStore((s) => s.setRadarResult);
  const [sources, setSources] = useState<RadarSource[]>([]);
  const [config, setConfig] = useState<RadarConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watched, setWatched] = useState<Set<string>>(new Set());

  useEffect(() => {
    api
      .watchlist()
      .then((w) => setWatched(new Set(w.map((x) => x.ticker))))
      .catch(() => {});
    api
      .radarSources()
      .then(({ predefined, defaults }) => {
        setSources(predefined);
        let cfg = defaults;
        try {
          const saved = localStorage.getItem(CFG_KEY);
          if (saved) cfg = { ...defaults, ...JSON.parse(saved) };
        } catch {
          /* usa defaults */
        }
        setConfig(cfg);
      })
      .catch((e) => setError((e as Error).message));
  }, [lang]);

  function openStock(e: React.MouseEvent, sym: string) {
    // Deja pasar Ctrl/⌘/Shift para "abrir en pestaña/ventana nueva".
    if (e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    setTicker(sym);
  }

  async function toggleWatch(e: React.MouseEvent, ticker: string) {
    e.stopPropagation();
    const next = new Set(watched);
    if (watched.has(ticker)) {
      await api.watchlistRemove(ticker);
      next.delete(ticker);
    } else {
      await api.watchlistAdd(ticker);
      next.add(ticker);
    }
    setWatched(next);
  }

  async function scan() {
    if (!config) return;
    setBusy(true);
    setError(null);
    localStorage.setItem(CFG_KEY, JSON.stringify(config));
    try {
      setResult(await api.radarScan(config));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!config) {
    return (
      <p className="text-[var(--color-muted)]">
        {lang === "en" ? "Loading radar…" : "Cargando radar…"}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">
          {lang === "en"
            ? "🔎 Technical opportunities radar"
            : "🔎 Radar de oportunidades técnicas"}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-muted)]">
          {lang === "en"
            ? "Scans Yahoo's dynamic lists and ranks stocks by confluence of bullish breakout signals. It's a screener to research, not a prediction or advice."
            : "Escanea listas dinámicas de Yahoo y rankea los valores por confluencia de señales de rompimiento alcista. Es un buscador para investigar, no una predicción ni asesoramiento."}
        </p>
      </div>

      <RadarConfigPanel
        sources={sources}
        config={config}
        setConfig={setConfig}
        busy={busy}
        onScan={scan}
      />

      {error && <p className="text-sm text-[var(--color-bear)]">{error}</p>}

      {result && (
        <RadarResults
          result={result}
          watched={watched}
          onOpen={openStock}
          onToggleWatch={toggleWatch}
        />
      )}
    </div>
  );
}
