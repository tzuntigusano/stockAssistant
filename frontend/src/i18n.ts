import { useStore } from "./store/useStore";
import type { Lang } from "./store/useStore";

export type { Lang };

/** Hook: idioma actual (re-renderiza al cambiarlo). */
export function useLang(): Lang {
  return useStore((s) => s.lang);
}

/** Idioma actual fuera de React (para helpers de formato). */
export function currentLang(): Lang {
  return useStore.getState().lang;
}

export function localeFor(lang: Lang): string {
  return lang === "en" ? "en-US" : "es-ES";
}
