import { useEffect, useState } from "react";
import { api } from "../api";
import type { SetupAlert } from "../types";
import { useLang, currentLang } from "../i18n";

const TFS = ["15m", "1h", "4h", "1d", "1wk"];

const T = {
  es: {
    title: "🎯 Alertas de setup",
    intro:
      "Vigila una EMA de principio a fin: te avisa en cada fase — rotura, retest y rebote con volumen.",
    empty: "Aún no hay ninguna. Arma una abajo.",
    direction: "Dirección",
    long: "Largo (rebote alcista)",
    short: "Corto (rechazo bajista)",
    tf: "Temporalidad",
    ema: "EMA",
    note: "Nota (opcional)",
    notePh: "ej. mi setup de continuación",
    arm: "Armar alerta",
    delete: "Eliminar",
    pause: "Pausar",
    resume: "Reactivar",
    paused: "en pausa",
    phase: {
      armed: "Esperando rotura",
      broken: "Rota · esperando retest",
      retest: "Retest en curso",
      confirmed: "✅ Rebote confirmado",
    } as Record<string, string>,
  },
  en: {
    title: "🎯 Setup alerts",
    intro:
      "Watches an EMA end-to-end: it alerts you at each phase — breakout, retest and bounce with volume.",
    empty: "None yet. Arm one below.",
    direction: "Direction",
    long: "Long (bullish bounce)",
    short: "Short (bearish rejection)",
    tf: "Timeframe",
    ema: "EMA",
    note: "Note (optional)",
    notePh: "e.g. my continuation setup",
    arm: "Arm alert",
    delete: "Delete",
    pause: "Pause",
    resume: "Resume",
    paused: "paused",
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

export default function SetupAlertsPanel({ ticker }: { ticker: string }) {
  const t = T[useLang()];
  const [setups, setSetups] = useState<SetupAlert[]>([]);
  const [direction, setDirection] = useState<"long" | "short">("long");
  const [tf, setTf] = useState("1d");
  const [length, setLength] = useState("200");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setSetups(await api.setups(ticker));
    } catch {
      /* ignora */
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  async function arm() {
    setBusy(true);
    try {
      await api.createSetup({
        ticker,
        tf,
        length: Math.max(1, Math.min(400, parseInt(length, 10) || 50)),
        direction,
        note: note.trim() || undefined,
        lang: currentLang(),
      });
      setNote("");
      load();
    } catch {
      /* ignora */
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    await api.deleteSetup(id);
    load();
  }

  async function toggle(s: SetupAlert) {
    await api.toggleSetup(s.id, !s.active);
    load();
  }

  return (
    <div className="card">
      <div className="card-title">{t.title}</div>
      <p className="mb-3 text-xs text-[var(--color-muted)]">{t.intro}</p>

      {setups.length > 0 ? (
        <ul className="mb-4 space-y-2">
          {setups.map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between rounded-lg bg-[var(--color-panel-2)] px-3 py-2 text-sm"
            >
              <span className={s.active ? "" : "opacity-50"}>
                <span className="font-medium">
                  EMA{s.length} · {s.tf} · {s.direction === "long" ? "▲" : "▼"}
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
                  onClick={() => toggle(s)}
                  className="text-xs text-[var(--color-muted)] hover:text-white"
                  title={s.active ? t.pause : t.resume}
                >
                  {s.active ? "⏸" : "▶"}
                </button>
                <button
                  onClick={() => remove(s.id)}
                  className="text-[var(--color-muted)] hover:text-[var(--color-bear)]"
                  title={t.delete}
                >
                  ✕
                </button>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mb-4 text-sm text-[var(--color-muted)]">{t.empty}</p>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[150px] flex-1">
          <label className="stat-label">{t.direction}</label>
          <select
            className="input mt-1"
            value={direction}
            onChange={(e) => setDirection(e.target.value as "long" | "short")}
          >
            <option value="long">{t.long}</option>
            <option value="short">{t.short}</option>
          </select>
        </div>
        <div className="w-24">
          <label className="stat-label">{t.tf}</label>
          <select className="input mt-1" value={tf} onChange={(e) => setTf(e.target.value)}>
            {TFS.map((x) => (
              <option key={x} value={x}>
                {x}
              </option>
            ))}
          </select>
        </div>
        <div className="w-20">
          <label className="stat-label">{t.ema}</label>
          <input
            className="input mt-1"
            inputMode="numeric"
            value={length}
            onChange={(e) => setLength(e.target.value)}
          />
        </div>
        <div className="min-w-[140px] flex-1">
          <label className="stat-label">{t.note}</label>
          <input
            className="input mt-1"
            placeholder={t.notePh}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        <button className="btn" onClick={arm} disabled={busy}>
          {t.arm}
        </button>
      </div>
    </div>
  );
}
