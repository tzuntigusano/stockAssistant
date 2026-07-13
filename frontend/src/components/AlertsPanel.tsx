import { useEffect, useState } from "react";
import { api } from "../api";
import type { Alert } from "../types";
import { fmtNum } from "../helpers";
import { useLang } from "../i18n";

const TYPES: { value: string; needsThreshold: boolean }[] = [
  { value: "price_above", needsThreshold: true },
  { value: "price_below", needsThreshold: true },
  { value: "rsi_above", needsThreshold: true },
  { value: "rsi_below", needsThreshold: true },
  { value: "break_resistance", needsThreshold: false },
  { value: "break_support", needsThreshold: false },
];

const T = {
  es: {
    title: "🔔 Alertas",
    empty:
      "Crea avisos: cuando se cumplan, aparecerán en la campana de arriba mientras la app esté abierta.",
    condition: "Condición",
    value: "Valor",
    noteOpt: "Nota (opcional)",
    notePh: "ej. entrar si rompe con volumen",
    add: "Añadir alerta",
    delete: "Eliminar",
    needThreshold: "Introduce un valor umbral.",
    types: {
      price_above: "Precio por encima de",
      price_below: "Precio por debajo de",
      rsi_above: "RSI por encima de",
      rsi_below: "RSI por debajo de",
      break_resistance: "Rotura de resistencia",
      break_support: "Pérdida de soporte",
    } as Record<string, string>,
  },
  en: {
    title: "🔔 Alerts",
    empty: "Create alerts: when triggered, they appear in the bell above while the app is open.",
    condition: "Condition",
    value: "Value",
    noteOpt: "Note (optional)",
    notePh: "e.g. enter if it breaks with volume",
    add: "Add alert",
    delete: "Delete",
    needThreshold: "Enter a threshold value.",
    types: {
      price_above: "Price above",
      price_below: "Price below",
      rsi_above: "RSI above",
      rsi_below: "RSI below",
      break_resistance: "Resistance breakout",
      break_support: "Support breakdown",
    } as Record<string, string>,
  },
} as const;

export default function AlertsPanel({ ticker }: { ticker: string }) {
  const t = T[useLang()];
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [type, setType] = useState(TYPES[0].value);
  const [threshold, setThreshold] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsThreshold = TYPES.find((t) => t.value === type)?.needsThreshold;

  async function load() {
    try {
      setAlerts(await api.alerts(ticker));
    } catch {
      /* ignora */
    }
  }

  useEffect(() => {
    load();
  }, [ticker]);

  async function add() {
    setError(null);
    let thr: number | null = null;
    if (needsThreshold) {
      thr = parseFloat(threshold.replace(",", "."));
      if (!thr) {
        setError(t.needThreshold);
        return;
      }
    }
    setBusy(true);
    try {
      await api.addAlert({ ticker, type, threshold: thr, note: note.trim() || undefined });
      setThreshold("");
      setNote("");
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    await api.deleteAlert(id);
    load();
  }

  return (
    <div className="card">
      <div className="card-title">{t.title}</div>

      {alerts.length > 0 ? (
        <ul className="mb-4 space-y-2">
          {alerts.map((a) => (
            <li
              key={a.id}
              className="flex items-center justify-between rounded-lg bg-[var(--color-panel-2)] px-3 py-2 text-sm"
            >
              <span>
                {t.types[a.type] ?? a.label}
                {a.threshold != null && <span className="font-medium"> {fmtNum(a.threshold)}</span>}
                {a.note && (
                  <span className="block text-xs text-[var(--color-muted)]">📝 {a.note}</span>
                )}
              </span>
              <button
                onClick={() => remove(a.id)}
                className="text-[var(--color-muted)] hover:text-[var(--color-bear)]"
                title={t.delete}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mb-4 text-sm text-[var(--color-muted)]">{t.empty}</p>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[180px] flex-1">
          <label className="stat-label">{t.condition}</label>
          <select className="input mt-1" value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES.map((ty) => (
              <option key={ty.value} value={ty.value}>
                {t.types[ty.value]}
              </option>
            ))}
          </select>
        </div>
        {needsThreshold && (
          <div className="w-28">
            <label className="stat-label">{t.value}</label>
            <input
              className="input mt-1"
              inputMode="decimal"
              placeholder="0,00"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          </div>
        )}
        <div className="min-w-[160px] flex-1">
          <label className="stat-label">{t.noteOpt}</label>
          <input
            className="input mt-1"
            placeholder={t.notePh}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        <button className="btn" onClick={add} disabled={busy}>
          {t.add}
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-[var(--color-bear)]">{error}</p>}
    </div>
  );
}
