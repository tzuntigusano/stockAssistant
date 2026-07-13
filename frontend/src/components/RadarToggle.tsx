import { useEffect, useState } from "react";
import { api } from "../api";
import { useLang } from "../i18n";

/** Checkbox de la ficha: marca el valor para el radar de rupturas en directo
 *  (lista separada de la watchlist general, sondeada cada ~45 s). */
export default function RadarToggle({ ticker }: { ticker: string }) {
  const lang = useLang();
  const [on, setOn] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .radarwatchStatus(ticker)
      .then((r) => !cancelled && setOn(r.in_radar))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  async function toggle() {
    if (on) {
      await api.radarwatchRemove(ticker);
      setOn(false);
    } else {
      await api.radarwatchAdd(ticker);
      setOn(true);
    }
  }

  return (
    <button
      onClick={toggle}
      title={
        lang === "en"
          ? "Watch live breakouts (every ~45 s during market hours)"
          : "Vigilar rupturas en directo (cada ~45 s en horario de mercado)"
      }
      className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition ${
        on
          ? "border-[var(--color-bull)] bg-[var(--color-bull)]/10 text-[var(--color-bull)]"
          : "border-[var(--color-line)] bg-[var(--color-panel-2)] text-[var(--color-ink)] hover:border-[var(--color-accent)]"
      }`}
    >
      <span
        className={`flex h-4 w-4 items-center justify-center rounded border text-[10px] ${
          on
            ? "border-[var(--color-bull)] bg-[var(--color-bull)] text-white"
            : "border-[var(--color-muted)]"
        }`}
      >
        {on ? "✓" : ""}
      </span>
      🚀 {lang === "en" ? "Watch breakouts" : "Vigilar rupturas"}
    </button>
  );
}
