// Vista de las CARTERAS FICTICIAS (paper trading): dos carteras con distinto
// horizonte compitiendo entre sí. Las decisiones las toma el backend de forma
// determinista; aquí solo se muestran, con sus stops/objetivos bien visibles.
import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type {
  PaperCompare,
  PaperLogEntry,
  PaperMode,
  PaperPortfolio,
  PaperPosition,
  PaperStatus,
} from "../types";
import { useStore } from "../store/useStore";
import { useLang } from "../i18n";
import { fmtMoney, fmtNum, fmtPct, signColor } from "../helpers";

const T = {
  es: {
    title: "🧪 Carteras ficticias",
    subtitle:
      "Dinero simulado. Las decisiones son deterministas (radar + confluencia de señales), no las improvisa una IA. Esto no es asesoramiento financiero.",
    modes: { normal: "Cartera normal", fast: "Cartera muy corto plazo" },
    modeHint: {
      normal: "Swing y medio plazo: stops anchos, deja correr las ganancias.",
      fast: "Horas / pocos días: objetivo del 3% y stops ceñidos, pero si la tendencia aguanta no cierra y estira la ganancia.",
    },
    marketOpen: "Mercado USA abierto",
    marketClosed: "Mercado USA cerrado",
    nyTime: "hora NY",
    auto: "Automático",
    autoOn: "Analiza solo cada 15 min con el mercado abierto",
    run: "🔄 Re-analizar ahora",
    runClosed: "👁️ Ver qué haría",
    running: "Analizando…",
    dryHint:
      "Con el mercado cerrado no hay precio real al que ejecutar: el análisis se hace igual, pero solo se anota en el diario lo que haría. No abre posiciones.",
    lastRun: "Último análisis",
    never: "todavía ninguno",
    equity: "Valor total",
    cash: "Caja libre",
    pnl: "P&L total",
    trades: "Operaciones",
    winRate: "% acierto",
    leader: "🏆 Va ganando",
    open: "Posiciones abiertas",
    closed: "Operaciones cerradas",
    noOpen: "Sin posiciones abiertas ahora mismo.",
    noClosed: "Todavía no se ha cerrado ninguna operación.",
    entry: "Entrada",
    now: "Actual",
    stop: "Stop",
    target: "Objetivo",
    exit: "Salida",
    days: "días",
    risk: "Riesgo",
    long: "LARGO",
    short: "CORTO",
    createAlerts: "🔔 Crear alertas",
    alertsDone: "✅ Alertas creadas",
    closeNow: "Cerrar",
    confirmClose: "¿Cerrar esta posición ficticia al precio actual?",
    diary: "📓 Diario",
    noDiary: "Sin actividad todavía. Pulsa «Re-analizar ahora» para empezar.",
    reset: "Reiniciar cartera",
    confirmReset: "¿Borrar todas las operaciones de esta cartera y reponer el capital inicial?",
    rules: "Reglas",
    riskPer: "riesgo por operación",
    maxPos: "posiciones máx.",
    minScore: "confluencia mín.",
    maxHold: "plazo máx.",
    stopMoved: "stop movido",
    runner: "🚀 dejando correr",
    runnerHint:
      "Superó el objetivo pero la tendencia sigue fuerte (precio sobre EMA20 + MACD alcista + RSI en zona de fuerza), así que en vez de cerrar sube el stop y aguanta.",
  },
  en: {
    title: "🧪 Paper portfolios",
    subtitle:
      "Simulated money. Decisions are deterministic (radar + signal confluence), not improvised by an AI. This is not financial advice.",
    modes: { normal: "Core portfolio", fast: "Very short-term portfolio" },
    modeHint: {
      normal: "Swing and medium term: wider stops, lets winners run.",
      fast: "Hours / a few days: 3% target and tight stops, but if the trend holds it keeps running instead of closing.",
    },
    marketOpen: "US market open",
    marketClosed: "US market closed",
    nyTime: "NY time",
    auto: "Automatic",
    autoOn: "Runs by itself every 15 min while the market is open",
    run: "🔄 Re-run analysis",
    runClosed: "👁️ Preview what it would do",
    running: "Analysing…",
    dryHint:
      "With the market closed there is no real price to fill at: the analysis still runs, but it only records what it would do in the diary. It opens no positions.",
    lastRun: "Last run",
    never: "none yet",
    equity: "Total value",
    cash: "Free cash",
    pnl: "Total P&L",
    trades: "Trades",
    winRate: "Win rate",
    leader: "🏆 Leading",
    open: "Open positions",
    closed: "Closed trades",
    noOpen: "No open positions right now.",
    noClosed: "No trade has been closed yet.",
    entry: "Entry",
    now: "Now",
    stop: "Stop",
    target: "Target",
    exit: "Exit",
    days: "days",
    risk: "Risk",
    long: "LONG",
    short: "SHORT",
    createAlerts: "🔔 Create alerts",
    alertsDone: "✅ Alerts created",
    closeNow: "Close",
    confirmClose: "Close this paper position at the current price?",
    diary: "📓 Diary",
    noDiary: "No activity yet. Hit “Re-run analysis” to get started.",
    reset: "Reset portfolio",
    confirmReset: "Delete every trade in this portfolio and restore the initial capital?",
    rules: "Rules",
    riskPer: "risk per trade",
    maxPos: "max positions",
    minScore: "min confluence",
    maxHold: "max holding",
    stopMoved: "stop moved",
    runner: "🚀 letting it run",
    runnerHint:
      "It passed the target but the trend is still strong (price above EMA20 + bullish MACD + RSI in strength zone), so instead of closing it raises the stop and holds.",
  },
} as const;

const KIND_ICON: Record<string, string> = {
  entry: "🟢",
  exit: "🔴",
  stop: "🛡️",
  skip: "⏭️",
  cycle: "🕒",
  dryrun: "👁️",
  system: "⚙️",
};

function PositionCard({
  pos,
  t,
  onChanged,
}: {
  pos: PaperPosition;
  t: (typeof T)[keyof typeof T];
  onChanged: () => void;
}) {
  const setTicker = useStore((s) => s.setTicker);
  const [alerted, setAlerted] = useState(false);
  const [busy, setBusy] = useState(false);
  const long = pos.side === "long";
  const pnl = pos.unrealized_pnl ?? 0;

  return (
    <li className="rounded-lg bg-[var(--color-panel-2)] p-3">
      <div className="flex flex-wrap items-baseline gap-2">
        <button
          onClick={() => setTicker(pos.ticker)}
          className="text-base font-bold text-[var(--color-accent)] hover:underline"
          title={pos.name}
        >
          {pos.ticker}
        </button>
        <span
          className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
            long
              ? "bg-[var(--color-bull)]/15 text-[var(--color-bull)]"
              : "bg-[var(--color-bear)]/15 text-[var(--color-bear)]"
          }`}
        >
          {long ? `▲ ${t.long}` : `▼ ${t.short}`}
        </span>
        <span className="text-xs text-[var(--color-muted)]">
          {pos.horizon_label} · {fmtNum(pos.shares, 2)} × {fmtNum(pos.entry_price)}
        </span>
        {pos.runner && (
          <span
            className="rounded bg-[var(--color-accent)]/15 px-1.5 py-0.5 text-xs text-[var(--color-accent)]"
            title={t.runnerHint}
          >
            {t.runner}
          </span>
        )}
        <span className={`ml-auto text-right font-semibold ${signColor(pnl)}`}>
          {fmtMoney(pnl)} <span className="text-xs">({fmtPct(pos.unrealized_pnl_pct)})</span>
        </span>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-4">
        <div>
          <span className="text-[var(--color-muted)]">{t.entry}: </span>
          {fmtNum(pos.entry_price)}
        </div>
        <div>
          <span className="text-[var(--color-muted)]">{t.now}: </span>
          {fmtNum(pos.current_price)}
        </div>
        <div className="text-[var(--color-bear)]">
          <span className="text-[var(--color-muted)]">{t.stop}: </span>
          {fmtNum(pos.stop)}
          {pos.stop_moved && (
            <span className="ml-1 text-[var(--color-muted)]">({t.stopMoved})</span>
          )}
        </div>
        <div className="text-[var(--color-bull)]">
          <span className="text-[var(--color-muted)]">{t.target}: </span>
          {fmtNum(pos.target)}
          <span className="ml-1 text-[var(--color-muted)]">· {pos.rr}:1</span>
        </div>
      </div>

      <p className="mt-2 text-xs text-[var(--color-muted)]">
        📋 {pos.thesis} · {pos.days_held} {t.days}
      </p>

      <div className="mt-2 flex gap-2">
        <button
          className="btn-ghost text-xs"
          disabled={alerted || busy}
          onClick={async () => {
            setBusy(true);
            try {
              await api.paperPositionAlerts(pos.id);
              setAlerted(true);
            } finally {
              setBusy(false);
            }
          }}
          title={`${t.target} ${fmtNum(pos.target)} · ${t.stop} ${fmtNum(pos.stop)}`}
        >
          {alerted ? t.alertsDone : t.createAlerts}
        </button>
        <button
          className="btn-ghost text-xs"
          disabled={busy}
          onClick={async () => {
            if (!window.confirm(t.confirmClose)) return;
            setBusy(true);
            try {
              await api.paperClosePosition(pos.id);
              onChanged();
            } finally {
              setBusy(false);
            }
          }}
        >
          {t.closeNow}
        </button>
      </div>
    </li>
  );
}

function PortfolioPanel({
  p,
  mode,
  t,
  onChanged,
}: {
  p: PaperPortfolio;
  mode: PaperMode;
  t: (typeof T)[keyof typeof T];
  onChanged: () => void;
}) {
  const setTicker = useStore((s) => s.setTicker);
  const c = p.config;

  return (
    <div className="card space-y-3">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 className="font-bold">{t.modes[mode]}</h2>
        <span className="text-xs text-[var(--color-muted)]">{t.modeHint[mode]}</span>
        <button
          className="ml-auto text-xs text-[var(--color-muted)] hover:text-[var(--color-bear)]"
          onClick={async () => {
            if (!window.confirm(t.confirmReset)) return;
            await api.paperReset(mode);
            onChanged();
          }}
        >
          {t.reset}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        <div>
          <div className="text-xs text-[var(--color-muted)]">{t.equity}</div>
          <div className="font-semibold">{fmtMoney(p.equity)}</div>
        </div>
        <div>
          <div className="text-xs text-[var(--color-muted)]">{t.pnl}</div>
          <div className={`font-semibold ${signColor(p.total_pnl)}`}>
            {fmtMoney(p.total_pnl)} ({fmtPct(p.total_pnl_pct)})
          </div>
        </div>
        <div>
          <div className="text-xs text-[var(--color-muted)]">{t.cash}</div>
          <div>{fmtMoney(p.cash)}</div>
        </div>
        <div>
          <div className="text-xs text-[var(--color-muted)]">
            {t.trades} / {t.winRate}
          </div>
          <div>
            {p.trades} · {p.win_rate === null ? "—" : `${fmtNum(p.win_rate, 0)}%`}
          </div>
        </div>
      </div>

      <p className="text-xs text-[var(--color-muted)]">
        {t.rules}: {c.risk_pct}% {t.riskPer} · {c.max_positions} {t.maxPos} · {t.minScore}{" "}
        {c.min_score} · {t.maxHold} {c.max_hold_days} {t.days}
      </p>

      <div>
        <div className="card-title">
          {t.open} ({p.open_positions.length})
        </div>
        {p.open_positions.length === 0 ? (
          <p className="text-sm text-[var(--color-muted)]">{t.noOpen}</p>
        ) : (
          <ul className="space-y-2">
            {p.open_positions.map((pos) => (
              <PositionCard key={pos.id} pos={pos} t={t} onChanged={onChanged} />
            ))}
          </ul>
        )}
      </div>

      <div>
        <div className="card-title">{t.closed}</div>
        {p.closed_positions.length === 0 ? (
          <p className="text-sm text-[var(--color-muted)]">{t.noClosed}</p>
        ) : (
          <ul className="space-y-1">
            {p.closed_positions.map((pos) => (
              <li
                key={pos.id}
                className="flex flex-wrap items-baseline gap-2 rounded bg-[var(--color-panel-2)] px-2 py-1.5 text-xs"
              >
                <button
                  onClick={() => setTicker(pos.ticker)}
                  className="font-semibold text-[var(--color-accent)] hover:underline"
                >
                  {pos.ticker}
                </button>
                <span className="text-[var(--color-muted)]">
                  {pos.side === "long" ? "▲" : "▼"} {fmtNum(pos.entry_price)} →{" "}
                  {fmtNum(pos.exit_price)} · {pos.exit_reason_label}
                </span>
                <span className={`ml-auto font-semibold ${signColor(pos.pnl ?? 0)}`}>
                  {fmtMoney(pos.pnl ?? 0)} ({fmtPct(pos.pnl_pct)})
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function PaperView() {
  const lang = useLang();
  const t = T[lang];
  const [data, setData] = useState<PaperCompare | null>(null);
  const [status, setStatus] = useState<PaperStatus | null>(null);
  const [log, setLog] = useState<PaperLogEntry[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [c, s, l] = await Promise.all([api.paperCompare(), api.paperStatus(), api.paperLog()]);
      setData(c);
      setStatus(s);
      setLog(l.entries);
    } catch (e) {
      setError((e as Error).message);
    }
    // `lang` no se usa aquí, pero el backend traduce horizontes y motivos de
    // salida: al cambiar de idioma hay que volver a pedirlo.
  }, [lang]);

  useEffect(() => {
    load();
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [load]);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      await api.paperRun();
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  const open = status?.market_open;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold">{t.title}</h1>
        <p className="mt-1 text-sm text-[var(--color-muted)]">{t.subtitle}</p>
      </div>

      <div className="card flex flex-wrap items-center gap-3">
        <span className="flex items-center gap-2 text-sm">
          <span
            className={`h-2 w-2 rounded-full ${
              open ? "bg-[var(--color-bull)]" : "bg-[var(--color-muted)]"
            }`}
          />
          {open ? t.marketOpen : t.marketClosed}
          {status && (
            <span className="text-xs text-[var(--color-muted)]">
              ({status.ny_time} {t.nyTime})
            </span>
          )}
        </span>

        <label className="flex items-center gap-2 text-sm" title={t.autoOn}>
          <input
            type="checkbox"
            checked={!!status?.enabled}
            onChange={async (e) => {
              await api.paperToggle(e.target.checked);
              load();
            }}
          />
          {t.auto}
        </label>

        <span className="text-xs text-[var(--color-muted)]">
          {t.lastRun}:{" "}
          {status?.last_run
            ? new Date(status.last_run * 1000).toLocaleTimeString(lang === "en" ? "en-US" : "es-ES")
            : t.never}
        </span>

        <button
          className="btn-ghost ml-auto text-sm"
          disabled={running}
          onClick={run}
          title={open ? undefined : t.dryHint}
        >
          {running ? t.running : open ? t.run : t.runClosed}
        </button>
      </div>

      {!open && <p className="text-xs text-[var(--color-muted)]">👁️ {t.dryHint}</p>}

      {error && <p className="card text-sm text-[var(--color-bear)]">{error}</p>}

      {data && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {(["normal", "fast"] as PaperMode[]).map((m) => (
              <div key={m} className="relative">
                {data.leader === m && data.portfolios[m].total_pnl !== 0 && (
                  <span className="absolute -top-2 right-2 z-10 rounded bg-[var(--color-accent)] px-1.5 py-0.5 text-xs text-white">
                    {t.leader}
                  </span>
                )}
                <PortfolioPanel p={data.portfolios[m]} mode={m} t={t} onChanged={load} />
              </div>
            ))}
          </div>

          <div className="card">
            <div className="card-title">{t.diary}</div>
            {log.length === 0 ? (
              <p className="text-sm text-[var(--color-muted)]">{t.noDiary}</p>
            ) : (
              <ul className="space-y-1 text-xs">
                {log.map((e) => (
                  <li key={e.id} className="flex gap-2">
                    <span className="shrink-0 text-[var(--color-muted)]">
                      {new Date(e.at * 1000).toLocaleTimeString(lang === "en" ? "en-US" : "es-ES", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <span className="shrink-0">{KIND_ICON[e.kind] ?? "·"}</span>
                    <span className="shrink-0 text-[var(--color-muted)]">[{t.modes[e.mode]}]</span>
                    <span>{e.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
