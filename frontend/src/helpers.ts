/** Utilidades de formato para la interfaz (locale según el idioma elegido). */

import { currentLang, localeFor } from "./i18n";

function locale(): string {
  return localeFor(currentLang());
}

export function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString(locale(), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function fmtMoney(v: number | null | undefined, currency = "USD", decimals = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  try {
    return v.toLocaleString(locale(), {
      style: "currency",
      currency,
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  } catch {
    return `${fmtNum(v, decimals)} ${currency}`;
  }
}

export function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v >= 0 ? "+" : ""}${fmtNum(v, 2)}%`;
}

export function fmtCompact(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const abs = Math.abs(v);
  const en = currentLang() === "en";
  if (abs >= 1e12) return `${fmtNum(v / 1e12, 2)} ${en ? "T" : "B"}`;
  if (abs >= 1e9) return `${fmtNum(v / 1e9, 2)} ${en ? "B" : "MM"}`;
  if (abs >= 1e6) return `${fmtNum(v / 1e6, 2)} M`;
  return fmtNum(v, 0);
}

/** URL de la ficha de un valor (para enlaces "abrir en pestaña nueva"). */
export function stockHref(sym: string): string {
  return `?stock=${encodeURIComponent(sym)}`;
}

/** Color según signo (verde alcista / rojo bajista). */
export function signColor(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return "text-[var(--color-muted)]";
  return v > 0 ? "text-[var(--color-bull)]" : "text-[var(--color-bear)]";
}
