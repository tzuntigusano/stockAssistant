// Vista central de TODAS mis alertas (clásicas + de setup), de todos los valores.
// Permite activar/pausar una a una o de forma masiva, y borrarlas.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Alert, SetupAlert } from "../types";
import { useStore } from "../store/useStore";
import { useLang } from "../i18n";
import { fmtNum } from "../helpers";

const T = {
  es: {
    title: "🔔 Mis alertas",
    subtitle: "Todas tus alertas, de todos los valores. Púlsalas para abrir su ficha.",
    classic: "Alertas de precio / indicadores",
    setups: "Alertas de setup",
    none: "No tienes alertas todavía.",
    activeCount: (a: number, n: number) => `${a} activas de ${n}`,
    pauseAll: "⏸ Pausar todas",
    resumeAll: "▶ Activar todas",
    confirmPause: "¿Pausar TODAS tus alertas? Podrás reactivarlas cuando quieras.",
    confirmResume: "¿Activar TODAS tus alertas?",
    pause: "Pausar",
    resume: "Activar",
    delete: "Eliminar",
    paused: "en pausa",
    trendline: "Trendline",
    types: {
      price_above: "Precio por encima de",
      price_below: "Precio por debajo de",
      rsi_above: "RSI por encima de",
      rsi_below: "RSI por debajo de",
      break_resistance: "Rotura de resistencia",
      break_support: "Pérdida de soporte",
    } as Record<string, string>,
    phase: {
      armed: "Esperando rotura",
      broken: "Rota · esperando retest",
      retest: "Retest en curso",
      confirmed: "✅ Rebote confirmado",
    } as Record<string, string>,
  },
  en: {
    title: "🔔 My alerts",
    subtitle: "All your alerts, across every stock. Click one to open its page.",
    classic: "Price / indicator alerts",
    setups: "Setup alerts",
    none: "You have no alerts yet.",
    activeCount: (a: number, n: number) => `${a} active of ${n}`,
    pauseAll: "⏸ Pause all",
    resumeAll: "▶ Enable all",
    confirmPause: "Pause ALL your alerts? You can re-enable them anytime.",
    confirmResume: "Enable ALL your alerts?",
    pause: "Pause",
    resume: "Enable",
    delete: "Delete",
    paused: "paused",
    trendline: "Trendline",
    types: {
      price_above: "Price above",
      price_below: "Price below",
      rsi_above: "RSI above",
      rsi_below: "RSI below",
      break_resistance: "Resistance breakout",
      break_support: "Support breakdown",
    } as Record<string, string>,
    phase: {
      armed: "Waiting for breakout",
      broken: "Broken · waiting for retest",
      retest: "Retesting",
      confirmed: "✅ Bounce confirmed",
    } as Record<string, string>,
  },
} as const;

const PHASE_COLOR: Record<string, string> = {
  armed: "var(--color-muted)",
  broken: "var(--color-accent)",
  retest: "#eab308",
  confirmed: "var(--color-bull)",
};

export default function AlertsView() {
  const t = T[useLang()];
  const setTicker = useStore((s) => s.setTicker);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [setups, setSetups] = useState<SetupAlert[]>([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [a, s] = await Promise.all([api.alerts(), api.setups()]);
      setAlerts(a);
      setSetups(s);
    } catch {
      /* ignora */
    }
  }

  useEffect(() => {
    load();
  }, []);

  const total = alerts.length + setups.length;
  const active = alerts.filter((a) => a.active).length + setups.filter((s) => s.active).length;

  async function toggleAll(next: boolean) {
    if (!window.confirm(next ? t.confirmResume : t.confirmPause)) return;
    setBusy(true);
    try {
      await Promise.all([api.toggleAllAlerts(next), api.toggleAllSetups(next)]);
      await load();
    } finally {
      setBusy(false);
    }
  }

  const rowCls =
    "flex items-center justify-between gap-2 rounded-lg bg-[var(--color-panel-2)] px-3 py-2 text-sm";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold">{t.title}</h1>
        <p className="mt-1 text-sm text-[var(--color-muted)]">{t.subtitle}</p>
      </div>

      {total > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-[var(--color-muted)]">{t.activeCount(active, total)}</span>
          <div className="ml-auto flex gap-2">
            <button className="btn-ghost text-xs" disabled={busy} onClick={() => toggleAll(false)}>
              {t.pauseAll}
            </button>
            <button className="btn-ghost text-xs" disabled={busy} onClick={() => toggleAll(true)}>
              {t.resumeAll}
            </button>
          </div>
        </div>
      )}

      {total === 0 && <p className="card text-sm text-[var(--color-muted)]">{t.none}</p>}

      {alerts.length > 0 && (
        <div className="card">
          <div className="card-title">{t.classic}</div>
          <ul className="space-y-2">
            {alerts.map((a) => (
              <li key={a.id} className={rowCls}>
                <span className={a.active ? "" : "opacity-50"}>
                  <button
                    onClick={() => setTicker(a.ticker)}
                    className="font-semibold text-[var(--color-accent)] hover:underline"
                  >
                    {a.ticker}
                  </button>{" "}
                  <span className="text-[var(--color-muted)]">
                    {t.types[a.type] ?? a.label}
                    {a.threshold != null && (
                      <span className="font-medium text-[var(--color-ink)]">
                        {" "}
                        {fmtNum(a.threshold)}
                      </span>
                    )}
                  </span>
                  {!a.active && (
                    <span className="ml-2 text-xs text-[var(--color-muted)]">({t.paused})</span>
                  )}
                  {a.note && (
                    <span className="block text-xs text-[var(--color-muted)]">📝 {a.note}</span>
                  )}
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <button
                    onClick={async () => {
                      await api.toggleAlert(a.id, !a.active);
                      load();
                    }}
                    title={a.active ? t.pause : t.resume}
                    className="text-xs text-[var(--color-muted)] hover:text-white"
                  >
                    {a.active ? "⏸" : "▶"}
                  </button>
                  <button
                    onClick={async () => {
                      await api.deleteAlert(a.id);
                      load();
                    }}
                    title={t.delete}
                    className="text-[var(--color-muted)] hover:text-[var(--color-bear)]"
                  >
                    ✕
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {setups.length > 0 && (
        <div className="card">
          <div className="card-title">{t.setups}</div>
          <ul className="space-y-2">
            {setups.map((s) => (
              <li key={s.id} className={rowCls}>
                <span className={s.active ? "" : "opacity-50"}>
                  <button
                    onClick={() => setTicker(s.ticker)}
                    className="font-semibold text-[var(--color-accent)] hover:underline"
                  >
                    {s.ticker}
                  </button>{" "}
                  <span className="text-[var(--color-muted)]">
                    {s.level_type === "trendline" ? t.trendline : `EMA${s.length}`} · {s.tf} ·{" "}
                    {s.direction === "long" ? "▲" : "▼"}
                  </span>
                  <span
                    className="ml-2 rounded px-1.5 py-0.5 text-xs"
                    style={{
                      color: PHASE_COLOR[s.state],
                      border: `1px solid ${PHASE_COLOR[s.state]}`,
                    }}
                  >
                    {t.phase[s.state]}
                  </span>
                  {!s.active && (
                    <span className="ml-2 text-xs text-[var(--color-muted)]">({t.paused})</span>
                  )}
                  {s.note && (
                    <span className="block text-xs text-[var(--color-muted)]">📝 {s.note}</span>
                  )}
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <button
                    onClick={async () => {
                      await api.toggleSetup(s.id, !s.active);
                      load();
                    }}
                    title={s.active ? t.pause : t.resume}
                    className="text-xs text-[var(--color-muted)] hover:text-white"
                  >
                    {s.active ? "⏸" : "▶"}
                  </button>
                  <button
                    onClick={async () => {
                      await api.deleteSetup(s.id);
                      load();
                    }}
                    title={t.delete}
                    className="text-[var(--color-muted)] hover:text-[var(--color-bear)]"
                  >
                    ✕
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
