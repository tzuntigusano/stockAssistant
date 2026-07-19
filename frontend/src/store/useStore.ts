import { create } from "zustand";
import type { ChartCommand, RadarResult } from "../types";

export type Lang = "es" | "en";
type View = "dashboard" | "radar" | "alerts" | "paper";

interface NavState {
  ticker: string | null;
  view: View;
}

interface AppState {
  ticker: string | null;
  view: View;
  recents: string[];
  history: NavState[];
  radarResult: RadarResult | null;
  // Puente chat ↔ LiveChart: el gráfico publica su estado; el chat manda comandos.
  chartState: string;
  chartCommand: (ChartCommand & { _id: number }) | null;
  lang: Lang;
  setLang: (l: Lang) => void;
  setTicker: (t: string) => void;
  setView: (v: View) => void;
  goHome: () => void;
  goBack: () => void;
  setRadarResult: (r: RadarResult | null) => void;
  setChartState: (s: string) => void;
  applyChartCommand: (c: ChartCommand) => void;
}

const RECENTS_KEY = "sa_recents";

function loadRecents(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENTS_KEY) || "[]");
  } catch {
    return [];
  }
}

export const useStore = create<AppState>((set, get) => ({
  ticker: null,
  view: "dashboard",
  recents: loadRecents(),
  history: [],
  radarResult: null,
  chartState: "desconocido",
  chartCommand: null,
  lang: (localStorage.getItem("sa_lang") as Lang) || "es",

  setTicker: (t: string) => {
    const sym = t.toUpperCase();
    const { ticker, view, history, recents } = get();
    // No apiles si ya estamos en esa misma ficha.
    if (ticker === sym) return;
    const newRecents = [sym, ...recents.filter((r) => r !== sym)].slice(0, 8);
    localStorage.setItem(RECENTS_KEY, JSON.stringify(newRecents));
    set({
      history: [...history, { ticker, view }],
      ticker: sym,
      recents: newRecents,
    });
  },

  setView: (v: View) => {
    const { ticker, view, history } = get();
    if (!ticker && view === v) return; // ya estamos ahí
    set({ history: [...history, { ticker, view }], ticker: null, view: v });
  },

  goHome: () => set({ ticker: null, view: "dashboard", history: [] }),

  goBack: () => {
    const { history } = get();
    if (history.length === 0) {
      set({ ticker: null, view: "dashboard" });
      return;
    }
    const prev = history[history.length - 1];
    set({
      ticker: prev.ticker,
      view: prev.view,
      history: history.slice(0, -1),
    });
  },

  setRadarResult: (r: RadarResult | null) => set({ radarResult: r }),

  setChartState: (s: string) => set({ chartState: s }),
  applyChartCommand: (c: ChartCommand) => set({ chartCommand: { ...c, _id: Date.now() } }),

  setLang: (l: Lang) => {
    localStorage.setItem("sa_lang", l);
    set({ lang: l });
  },
}));
