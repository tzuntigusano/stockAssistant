// Botón para reiniciar el backend desde la app. Útil cuando la sesión de
// yfinance se degrada tras muchas horas (empiezan errores 500 al abrir valores).
// Llama al endpoint, espera a que /health vuelva y recarga la página.
import { useState } from "react";
import { api } from "../api";
import { useLang } from "../i18n";

const T = {
  es: {
    idle: "Reiniciar backend",
    confirm: "¿Reiniciar el backend? Tardará unos segundos y la app se recargará al terminar.",
    working: "Reiniciando…",
    fail: "No respondió; ábrelo con start.ps1",
  },
  en: {
    idle: "Restart backend",
    confirm: "Restart the backend? It takes a few seconds and the app reloads when done.",
    working: "Restarting…",
    fail: "No response; launch it with start.ps1",
  },
} as const;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function RestartButton() {
  const t = T[useLang()];
  const [state, setState] = useState<"idle" | "working" | "fail">("idle");

  async function restart() {
    if (state === "working") return;
    if (!window.confirm(t.confirm)) return;
    setState("working");
    try {
      await api.restartBackend();
    } catch {
      /* la respuesta puede cortarse si reinicia muy rápido; da igual */
    }
    await sleep(1500); // deja que se caiga
    for (let i = 0; i < 25; i++) {
      try {
        await api.health();
        window.location.reload();
        return;
      } catch {
        await sleep(1000);
      }
    }
    setState("fail");
  }

  return (
    <button
      onClick={restart}
      disabled={state === "working"}
      title={state === "fail" ? t.fail : t.idle}
      className="shrink-0 rounded-lg border border-[var(--color-line)] px-2 py-1.5 text-sm text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-ink)] disabled:opacity-60"
    >
      <span className={state === "working" ? "inline-block animate-spin" : ""}>⟳</span>
      {state === "working" && <span className="ml-1 hidden text-xs sm:inline">{t.working}</span>}
      {state === "fail" && <span className="ml-1 text-xs text-[var(--color-bear)]">!</span>}
    </button>
  );
}
