import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, streamText } from "../api";
import { useStore } from "../store/useStore";
import { useLang } from "../i18n";
import type { Levels, ModelsStatus, StrategyModules } from "../types";
import { fmtMoney } from "../helpers";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

const MODEL_KEY = "sa_ai_model";
const SEL_KEY = "sa_strategy_sel";

// Verbo de acción + algo "de gráfico" → probablemente una orden para el gráfico (ES + EN).
const CHART_VERB =
  /\b(mu[eé]stra|mu[eé]strame|ense[ñn]a|ense[ñn]ame|pon|ponme|quita|qu[ií]tame|a[ñn]ade|a[ñn][aá]deme|deja|oculta|activa|desactiva|cambia|mete|saca|dibuja|show|display|add|remove|hide|put|leave|toggle|change|draw|set|only)\b/i;
const CHART_NOUN =
  /\b(ema|emas|media|medias|volumen|volume|rsi|bollinger|soporte|soportes|support|resistencia|resistencias|resistance|gr[aá]fico|chart|indicador|indicadores|indicator|intervalo|interval|temporalidad|timeframe|vela|velas|candle|candles|4h|1h|5m|15m|diario|daily|semanal|weekly|mtf)\b/i;

function looksLikeChartCommand(text: string): boolean {
  return CHART_VERB.test(text) && CHART_NOUN.test(text);
}

const LS = {
  es: {
    suggestions: [
      "¿Qué invalidaría este escenario?",
      "¿Cómo afecta a mi posición?",
      "Muéstrame solo la EMA 200 en 4h",
      "Añade el volumen al gráfico",
    ],
    title: "🎯 Estrategia y chat (IA)",
    reconfig: "↻ Reconfigurar",
    model: "Modelo:",
    ollamaOff: "⚠️ Ollama no está corriendo (localhost:11434)",
    geminiOff: "⚠️ Falta GEMINI_API_KEY en backend/.env",
    local: "(local)",
    noPos: " (sin posición)",
    promptLabel: "Prompt que se enviará",
    intro1: "La IA redacta sobre datos ya calculados (indicadores, fundamentales y ",
    introBold: "tus compras",
    intro2: "); no inventa cifras. Después podrás seguir preguntándole.",
    analyzing: "Analizando…",
    generate: "Generar estrategia",
    you: "Tú",
    analyst: "Analista IA",
    askPlaceholder: "Pregunta sobre la estrategia…",
    send: "Enviar",
    lvSupport: "Soporte",
    lvResistance: "Resistencia",
    lvStop: "Stop sugerido",
    lvAvgCost: "Coste medio",
  },
  en: {
    suggestions: [
      "What would invalidate this scenario?",
      "How does it affect my position?",
      "Show only the 200 EMA in 4h",
      "Add volume to the chart",
    ],
    title: "🎯 Strategy & chat (AI)",
    reconfig: "↻ Reconfigure",
    model: "Model:",
    ollamaOff: "⚠️ Ollama is not running (localhost:11434)",
    geminiOff: "⚠️ Missing GEMINI_API_KEY in backend/.env",
    local: "(local)",
    noPos: " (no position)",
    promptLabel: "Prompt to be sent",
    intro1: "The AI writes about already-computed data (indicators, fundamentals and ",
    introBold: "your buys",
    intro2: "); it doesn't invent figures. Then you can keep asking.",
    analyzing: "Analyzing…",
    generate: "Generate strategy",
    you: "You",
    analyst: "AI analyst",
    askPlaceholder: "Ask about the strategy…",
    send: "Send",
    lvSupport: "Support",
    lvResistance: "Resistance",
    lvStop: "Suggested stop",
    lvAvgCost: "Avg. cost",
  },
} as const;

function Level({
  label,
  value,
  currency,
}: {
  label: string;
  value?: number | null;
  currency: string;
}) {
  if (value === undefined || value === null) return null;
  return (
    <div className="rounded-lg bg-[var(--color-panel-2)] p-2.5">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{fmtMoney(value, currency)}</div>
    </div>
  );
}

export default function StrategyChat({
  ticker,
  currency,
  hasPosition,
}: {
  ticker: string;
  currency: string;
  hasPosition: boolean;
}) {
  const lang = useLang();
  const L = LS[lang];
  const [messages, setMessages] = useState<Msg[]>([]);
  const [levels, setLevels] = useState<Levels | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<ModelsStatus | null>(null);
  const [model, setModel] = useState<string>(() => localStorage.getItem(MODEL_KEY) || "");
  const [mods, setMods] = useState<StrategyModules | null>(null);
  const [sel, setSel] = useState<Record<string, string>>(() => {
    try {
      return JSON.parse(localStorage.getItem(SEL_KEY) || "{}");
    } catch {
      return {};
    }
  });
  const chartState = useStore((s) => s.chartState);
  const applyChartCommand = useStore((s) => s.applyChartCommand);
  const endRef = useRef<HTMLDivElement>(null);

  const generated = messages.length > 0;
  const isOllama = model === "ollama";
  const available = isOllama ? !!models?.ollama_available : !!models?.gemini_available;

  // Carga los módulos (se recargan al cambiar de idioma para traducir labels).
  useEffect(() => {
    api
      .strategyModules()
      .then(setMods)
      .catch(() => {});
  }, [lang]);

  // Estado de modelos, una vez.
  useEffect(() => {
    api
      .modelsStatus()
      .then((m) => {
        setModels(m);
        setModel((cur) => cur || m.model);
      })
      .catch(() => {});
  }, []);

  // Fija defaults de los módulos cuando llegan (respetando lo guardado).
  useEffect(() => {
    if (!mods) return;
    setSel((cur) => {
      const next = { ...cur };
      for (const key of mods.order) {
        if (!next[key]) next[key] = mods.modules[key].default;
      }
      return next;
    });
  }, [mods]);

  // Al cambiar de valor, reinicia la conversación.
  useEffect(() => {
    setMessages([]);
    setLevels(null);
    setError(null);
  }, [ticker]);

  // Si no hay posición, no permitir "posición: sí" (hasPosition viene por prop y
  // se actualiza en cuanto añades una compra en LotsPanel).
  useEffect(() => {
    if (!hasPosition && sel.posicion === "si") setField("posicion", "no");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasPosition]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);

  function setField(key: string, value: string) {
    setSel((cur) => {
      const next = { ...cur, [key]: value };
      localStorage.setItem(SEL_KEY, JSON.stringify(next));
      return next;
    });
  }

  function chooseModel(m: string) {
    setModel(m);
    localStorage.setItem(MODEL_KEY, m);
  }

  // Previsualización del prompt: misma plantilla que usa el backend.
  function preview(): string {
    if (!mods) return "";
    const text = (mod: string) =>
      mods.modules[mod]?.options.find((o) => o.key === sel[mod])?.text ?? "";
    return mods.template
      .replace("{analisis}", text("analisis"))
      .replace("{ticker}", ticker)
      .replace("{posicion}", text("posicion"))
      .replace("{temporalidad}", text("temporalidad"))
      .replace("{objetivo}", text("objetivo"))
      .replace("{formato}", text("formato"));
  }

  function appendLast(chunk: string) {
    setMessages((m) => {
      const copy = [...m];
      copy[copy.length - 1] = {
        role: "assistant",
        content: copy[copy.length - 1].content + chunk,
      };
      return copy;
    });
  }

  async function generate() {
    setBusy(true);
    setError(null);
    setLevels(null);
    setMessages([
      { role: "user", content: preview() },
      { role: "assistant", content: "" },
    ]);
    try {
      await streamText(
        `/api/strategy/${ticker}/stream`,
        { method: "POST", body: JSON.stringify({ selections: sel, model, lang }) },
        appendLast,
        (meta) => setLevels(meta.levels)
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function ask(q: string) {
    const question = q.trim();
    if (!question || busy) return;
    setInput("");
    const history = [...messages, { role: "user" as const, content: question }];
    setMessages([...history, { role: "assistant", content: "" }]);
    setBusy(true);
    try {
      await streamText(
        `/api/chat/${ticker}/stream`,
        {
          method: "POST",
          body: JSON.stringify({
            history,
            model,
            chart_state: chartState,
            force_chart: looksLikeChartCommand(question),
            lang,
          }),
        },
        appendLast,
        (meta) => {
          if (meta && meta.chart) applyChartCommand(meta.chart);
        }
      );
    } catch (e) {
      appendLast(`⚠️ ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="card-title">
        <span>{L.title}</span>
        {generated && (
          <button
            onClick={() => setMessages([])}
            disabled={busy}
            className="ml-auto text-xs font-normal normal-case text-[var(--color-muted)] hover:text-[var(--color-accent)]"
          >
            {L.reconfig}
          </button>
        )}
      </div>

      {/* Selector de modelo */}
      <div className="mb-3 flex items-center gap-2">
        <span className="stat-label">{L.model}</span>
        <select
          value={model}
          onChange={(e) => chooseModel(e.target.value)}
          disabled={busy}
          className="rounded-md border border-[var(--color-line)] bg-[var(--color-panel-2)] px-2 py-1 text-xs text-[var(--color-ink)] outline-none"
        >
          {(models?.models ?? []).map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
        {!available && (
          <span className="text-xs text-[var(--color-bear)]">
            {isOllama ? L.ollamaOff : L.geminiOff}
          </span>
        )}
        {isOllama && available && (
          <span className="text-xs text-[var(--color-muted)]">{L.local}</span>
        )}
      </div>

      {!generated && (
        <>
          {/* Módulos del prompt */}
          {mods && (
            <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {mods.order.map((key) => (
                <label key={key} className="text-xs">
                  <span className="stat-label mb-1 block">{mods.modules[key].label}</span>
                  <select
                    value={sel[key] ?? mods.modules[key].default}
                    onChange={(e) => setField(key, e.target.value)}
                    disabled={busy}
                    className="w-full rounded-md border border-[var(--color-line)] bg-[var(--color-panel-2)] px-2 py-1.5 text-xs text-[var(--color-ink)] outline-none"
                  >
                    {mods.modules[key].options.map((o) => (
                      <option
                        key={o.key}
                        value={o.key}
                        disabled={key === "posicion" && o.key === "si" && !hasPosition}
                      >
                        {o.label}
                        {key === "posicion" && o.key === "si" && !hasPosition ? L.noPos : ""}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          )}

          {/* Previsualización del prompt */}
          <div className="mb-3 rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] p-3">
            <div className="stat-label mb-1">{L.promptLabel}</div>
            <p className="text-sm leading-relaxed text-[var(--color-ink)]/90">{preview()}</p>
          </div>

          <p className="mb-3 text-xs text-[var(--color-muted)]">
            {L.intro1}
            <strong>{L.introBold}</strong>
            {L.intro2}
          </p>
          <button className="btn" onClick={generate} disabled={busy || !available}>
            {busy ? L.analyzing : L.generate}
          </button>
        </>
      )}

      {error && <p className="mt-3 text-sm text-[var(--color-bear)]">{error}</p>}

      {/* Niveles operativos */}
      {levels && (
        <div className="mb-4 mt-1 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
          <Level label={L.lvSupport} value={levels.support} currency={currency} />
          <Level label={L.lvResistance} value={levels.resistance} currency={currency} />
          <Level label="EMA50" value={levels.ema50} currency={currency} />
          <Level label={L.lvStop} value={levels.suggested_stop} currency={currency} />
          <Level label={L.lvAvgCost} value={levels.avg_cost} currency={currency} />
        </div>
      )}

      {/* Conversación */}
      {generated && (
        <div className="space-y-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`rounded-lg p-3 text-sm ${
                m.role === "user"
                  ? "ml-auto max-w-[85%] bg-[var(--color-accent)]/15 text-[var(--color-ink)]"
                  : "bg-[var(--color-panel-2)] text-[var(--color-ink)]/90"
              }`}
            >
              <span className="mb-1 block text-xs text-[var(--color-muted)]">
                {m.role === "user" ? L.you : L.analyst}
              </span>
              {m.role === "assistant" ? (
                <div className="md">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                  {busy && i === messages.length - 1 && <span className="animate-pulse">▌</span>}
                </div>
              ) : (
                <p className="whitespace-pre-line leading-relaxed">{m.content}</p>
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>
      )}

      {/* Sugerencias + entrada (una vez generada la estrategia) */}
      {generated && (
        <div className="mt-4">
          <div className="mb-2 flex flex-wrap gap-2">
            {L.suggestions.map((s) => (
              <button
                key={s}
                className="btn-ghost text-xs"
                onClick={() => ask(s)}
                disabled={busy || !available}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              className="input"
              placeholder={L.askPlaceholder}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask(input)}
              disabled={busy || !available}
            />
            <button className="btn" onClick={() => ask(input)} disabled={busy || !available}>
              {L.send}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
