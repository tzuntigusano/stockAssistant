import { useState } from "react";
import type { RadarConfig, RadarSource } from "../../types";
import { NumField, PARAM_LABELS, WEIGHT_LABELS } from "./radarUi";
import { useLang } from "../../i18n";

const T = {
  es: {
    sources: "Fuentes de candidatos",
    myWatch: "Mi lista de seguimiento",
    addOwn: "Añadir valores propios (separados por comas)",
    minScore: "Puntuación mínima",
    maxResults: "Máx. resultados",
    maxScan: "Máx. a escanear",
    scanning: "Escaneando el mercado…",
    scan: "🔎 Escanear el mercado",
    hideAdv: "Ocultar ajustes ▲",
    showAdv: "⚙ Ajustes avanzados ▼",
    thresholds: "Umbrales",
    benchmark: "Índice de referencia",
    weights: "Pesos de cada señal (0 = desactivada)",
  },
  en: {
    sources: "Candidate sources",
    myWatch: "My watchlist",
    addOwn: "Add your own stocks (comma-separated)",
    minScore: "Min. score",
    maxResults: "Max. results",
    maxScan: "Max. to scan",
    scanning: "Scanning the market…",
    scan: "🔎 Scan the market",
    hideAdv: "Hide settings ▲",
    showAdv: "⚙ Advanced settings ▼",
    thresholds: "Thresholds",
    benchmark: "Benchmark index",
    weights: "Signal weights (0 = off)",
  },
} as const;

export default function RadarConfigPanel({
  sources,
  config,
  setConfig,
  busy,
  onScan,
}: {
  sources: RadarSource[];
  config: RadarConfig;
  setConfig: (c: RadarConfig) => void;
  busy: boolean;
  onScan: () => void;
}) {
  const lang = useLang();
  const t = T[lang];
  const [advanced, setAdvanced] = useState(false);

  const updateParam = (k: string, v: number) =>
    setConfig({ ...config, params: { ...config.params, [k]: v } });
  const updateWeight = (k: string, v: number) =>
    setConfig({ ...config, weights: { ...config.weights, [k]: v } });
  const toggleSource = (k: string) => {
    const has = config.sources.predefined.includes(k);
    setConfig({
      ...config,
      sources: {
        ...config.sources,
        predefined: has
          ? config.sources.predefined.filter((x) => x !== k)
          : [...config.sources.predefined, k],
      },
    });
  };

  return (
    <div className="card">
      <div className="card-title">{t.sources}</div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((s) => (
          <label
            key={s.key}
            className="flex cursor-pointer items-center gap-2 rounded-lg bg-[var(--color-panel-2)] px-3 py-2 text-sm"
          >
            <input
              type="checkbox"
              checked={config.sources.predefined.includes(s.key)}
              onChange={() => toggleSource(s.key)}
            />
            {s.label}
          </label>
        ))}
        <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-[var(--color-panel-2)] px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={config.sources.watchlist}
            onChange={(e) =>
              setConfig({
                ...config,
                sources: { ...config.sources, watchlist: e.target.checked },
              })
            }
          />
          {t.myWatch}
        </label>
      </div>
      <div className="mt-3">
        <label className="stat-label">{t.addOwn}</label>
        <input
          className="input mt-1"
          placeholder="ej. NOK, PLTR, SOFI"
          value={config.sources.custom.join(", ")}
          onChange={(e) =>
            setConfig({
              ...config,
              sources: {
                ...config.sources,
                custom: e.target.value
                  .split(",")
                  .map((x) => x.trim().toUpperCase())
                  .filter(Boolean),
              },
            })
          }
        />
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-4">
        <NumField
          label={t.minScore}
          value={config.min_score}
          onChange={(v) => setConfig({ ...config, min_score: v })}
        />
        <NumField
          label={t.maxResults}
          value={config.max_results}
          onChange={(v) => setConfig({ ...config, max_results: v })}
        />
        <NumField
          label={t.maxScan}
          value={config.max_universe}
          onChange={(v) => setConfig({ ...config, max_universe: v })}
        />
        <button className="btn" onClick={onScan} disabled={busy}>
          {busy ? t.scanning : t.scan}
        </button>
        <button className="btn-ghost text-xs" onClick={() => setAdvanced((a) => !a)}>
          {advanced ? t.hideAdv : t.showAdv}
        </button>
      </div>

      {advanced && (
        <div className="mt-4 grid grid-cols-1 gap-6 border-t border-[var(--color-line)] pt-4 lg:grid-cols-2">
          <div>
            <div className="stat-label mb-2">{t.thresholds}</div>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(PARAM_LABELS[lang]).map(([k, label]) => (
                <NumField
                  key={k}
                  label={label}
                  step={k === "vol_mult" || k === "atr_min_pct" || k === "min_price" ? 0.1 : 1}
                  value={Number(config.params[k])}
                  onChange={(v) => updateParam(k, v)}
                />
              ))}
              <div>
                <label className="stat-label">{t.benchmark}</label>
                <input
                  className="input mt-1"
                  value={String(config.params.benchmark)}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      params: { ...config.params, benchmark: e.target.value.toUpperCase() },
                    })
                  }
                />
              </div>
            </div>
          </div>
          <div>
            <div className="stat-label mb-2">{t.weights}</div>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(WEIGHT_LABELS[lang]).map(([k, label]) => (
                <NumField
                  key={k}
                  label={label}
                  value={config.weights[k] ?? 0}
                  onChange={(v) => updateWeight(k, v)}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
