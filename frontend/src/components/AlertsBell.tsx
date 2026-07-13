import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { BreakoutEvent, BreakoutStatus, TriggeredAlert } from "../types";
import { useStore } from "../store/useStore";
import { useLang } from "../i18n";

const T = {
  es: {
    bellTitle: "Alertas y rupturas",
    notifsHdr: "Avisos",
    clearTitle: "Borrar todos los avisos de la campana (no borra las reglas)",
    clearAll: "🗑️ Borrar todo",
    liveBreakouts: "🚀 Rupturas en directo",
    noBreakouts: "Sin rupturas recientes.",
    alerts: "🔔 Alertas",
    noAlerts: "Ninguna alerta activada.",
    radar: "Radar de rupturas",
    every: "Cada",
    marketOpen: "🟢 mercado abierto",
    marketClosed: "⚪ mercado cerrado",
    realtime: "⚡ tiempo real",
    delayed: "con retraso (Yahoo)",
    winNotifs: "Notificaciones de escritorio",
    test: "Probar",
    winUnavailable: "Notificaciones de escritorio no disponibles en este sistema.",
    sending: "Enviando…",
    sent: "✓ Enviada (mira la esquina de la pantalla)",
  },
  en: {
    bellTitle: "Alerts & breakouts",
    notifsHdr: "Notifications",
    clearTitle: "Clear all bell notifications (does not delete the rules)",
    clearAll: "🗑️ Clear all",
    liveBreakouts: "🚀 Live breakouts",
    noBreakouts: "No recent breakouts.",
    alerts: "🔔 Alerts",
    noAlerts: "No triggered alerts.",
    radar: "Breakout radar",
    every: "Every",
    marketOpen: "🟢 market open",
    marketClosed: "⚪ market closed",
    realtime: "⚡ real time",
    delayed: "delayed (Yahoo)",
    winNotifs: "Desktop notifications",
    test: "Test",
    winUnavailable: "Desktop notifications not available on this system.",
    sending: "Sending…",
    sent: "✓ Sent (check the corner of your screen)",
  },
} as const;

export default function AlertsBell() {
  const t = T[useLang()];
  const setTicker = useStore((s) => s.setTicker);
  const [triggered, setTriggered] = useState<TriggeredAlert[]>([]);
  const [breakouts, setBreakouts] = useState<BreakoutEvent[]>([]);
  const [radar, setRadar] = useState<BreakoutStatus | null>(null);
  const [open, setOpen] = useState(false);
  const [notif, setNotif] = useState<{ supported: boolean; enabled: boolean } | null>(null);
  const [testMsg, setTestMsg] = useState("");
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .notificationsStatus()
      .then(setNotif)
      .catch(() => {});
    api
      .breakoutsStatus()
      .then(setRadar)
      .catch(() => {});
  }, []);

  async function toggleNotif() {
    if (!notif) return;
    const r = await api.notificationsToggle(!notif.enabled);
    setNotif({ ...notif, enabled: r.enabled });
  }

  async function toggleRadar() {
    if (!radar) return;
    const r = await api.breakoutsToggle(!radar.enabled);
    setRadar({ ...radar, enabled: r.enabled });
  }

  async function testNotif() {
    setTestMsg(t.sending);
    try {
      await api.notificationsTest();
      setTestMsg(t.sent);
    } catch (e) {
      setTestMsg(`⚠️ ${(e as Error).message}`);
    }
  }

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      api
        .checkAlerts()
        .then((r) => !cancelled && setTriggered(r.triggered))
        .catch(() => {});
      api
        .breakoutsRecent()
        .then((r) => !cancelled && setBreakouts(r.triggered))
        .catch(() => {});
    };
    check();
    const id = setInterval(check, 60 * 1000); // cada 1 min
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const count = triggered.length + breakouts.length;

  function go(ticker: string) {
    setTicker(ticker);
    setOpen(false);
  }

  async function clearAll() {
    setTriggered([]);
    setBreakouts([]);
    await Promise.all([api.dismissAlerts().catch(() => {}), api.breakoutsClear().catch(() => {})]);
  }

  return (
    <div ref={boxRef} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative rounded-lg px-2 py-1 text-lg hover:bg-[var(--color-panel-2)]"
        title={t.bellTitle}
      >
        🔔
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-bear)] px-1 text-[10px] font-bold text-white">
            {count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-30 mt-1 w-80 overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] shadow-xl">
          {/* Cabecera con botón de borrar todo */}
          <div className="flex items-center justify-between border-b border-[var(--color-line)] px-3 py-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">
              {t.notifsHdr}
            </span>
            <button
              onClick={clearAll}
              disabled={count === 0}
              className="text-xs text-[var(--color-muted)] transition hover:text-[var(--color-bear)] disabled:opacity-40"
              title={t.clearTitle}
            >
              {t.clearAll}
            </button>
          </div>

          {/* Rupturas en directo */}
          <div className="border-b border-[var(--color-line)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">
            {t.liveBreakouts}
          </div>
          {breakouts.length === 0 ? (
            <p className="px-3 py-2 text-sm text-[var(--color-muted)]">{t.noBreakouts}</p>
          ) : (
            <ul>
              {breakouts.map((b, i) => (
                <li key={i}>
                  <button
                    onClick={() => go(b.ticker)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-[var(--color-panel)]"
                  >
                    <span className="font-semibold text-[var(--color-bull)]">🚀 {b.ticker}</span>{" "}
                    <span className="text-xs text-[var(--color-muted)]">{b.at}</span>
                    <div className="text-xs text-[var(--color-ink)]/80">{b.message}</div>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Alertas de precio / indicadores */}
          <div className="border-y border-[var(--color-line)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">
            {t.alerts}
          </div>
          {triggered.length === 0 ? (
            <p className="px-3 py-2 text-sm text-[var(--color-muted)]">{t.noAlerts}</p>
          ) : (
            <ul>
              {triggered.map((a) => (
                <li key={a.id}>
                  <button
                    onClick={() => go(a.ticker)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-[var(--color-panel)]"
                  >
                    <span className="font-semibold text-[var(--color-accent)]">{a.ticker}</span>{" "}
                    <span className="text-[var(--color-muted)]">{a.label}</span>
                    <div className="text-xs text-[var(--color-ink)]/80">{a.message}</div>
                    {a.note && <div className="text-xs text-[var(--color-muted)]">📝 {a.note}</div>}
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Ajustes */}
          <div className="space-y-3 border-t border-[var(--color-line)] p-3">
            {/* Radar de rupturas */}
            {radar && (
              <div>
                <label className="flex cursor-pointer items-center justify-between text-sm">
                  <span>{t.radar}</span>
                  <button
                    onClick={toggleRadar}
                    className={`relative h-5 w-9 rounded-full transition ${
                      radar.enabled ? "bg-[var(--color-bull)]" : "bg-[var(--color-line)]"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
                        radar.enabled ? "left-[18px]" : "left-0.5"
                      }`}
                    />
                  </button>
                </label>
                <p className="mt-1 text-xs text-[var(--color-muted)]">
                  {t.every} {radar.interval}s · {radar.market_open ? t.marketOpen : t.marketClosed}{" "}
                  · {radar.realtime ? `${t.realtime} (${radar.provider})` : t.delayed}
                </p>
              </div>
            )}

            {/* Notificaciones de Windows */}
            {notif?.supported ? (
              <div>
                <label className="flex cursor-pointer items-center justify-between text-sm">
                  <span>{t.winNotifs}</span>
                  <button
                    onClick={toggleNotif}
                    className={`relative h-5 w-9 rounded-full transition ${
                      notif.enabled ? "bg-[var(--color-bull)]" : "bg-[var(--color-line)]"
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
                        notif.enabled ? "left-[18px]" : "left-0.5"
                      }`}
                    />
                  </button>
                </label>
                <div className="mt-2 flex items-center gap-2">
                  <button className="btn-ghost text-xs" onClick={testNotif}>
                    {t.test}
                  </button>
                  {testMsg && <span className="text-xs text-[var(--color-muted)]">{testMsg}</span>}
                </div>
              </div>
            ) : (
              <p className="text-xs text-[var(--color-muted)]">{t.winUnavailable}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
