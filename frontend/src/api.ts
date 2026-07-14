import type {
  Alert,
  Analysis,
  BreakoutEvent,
  BreakoutScore,
  BreakoutStatus,
  ChartBundle,
  FeedPost,
  LinePoint,
  Lot,
  ModelsStatus,
  NewsItem,
  Portfolio,
  Position,
  RadarConfig,
  RadarResult,
  RadarSource,
  SearchResult,
  Sentiment,
  SetupAlert,
  Strategy,
  StrategyModules,
  TrendLine,
  TriggeredAlert,
  WatchlistItem,
} from "./types";
import { currentLang } from "./i18n";

async function req<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let msg = `Error ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) msg = body.detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(msg);
  }
  return res.json();
}

// --- Limitador de concurrencia para las llamadas que pegan a Yahoo ---
// Al abrir una ficha con la caché fría se dispara una ráfaga de peticiones y
// Yahoo puede responder 429. Servirlas de MAX_CONCURRENT en MAX_CONCURRENT las
// escalona y evita el límite. Cuando la caché está caliente las respuestas
// llegan en ms y la cola se vacía al instante, así que en la práctica va "de una".
const MAX_CONCURRENT = 2;
let gateActive = 0;
const gateQueue: (() => void)[] = [];
let gatePending = 0; // en curso + en cola (para el aviso de carga)
const pendingListeners = new Set<(n: number) => void>();

function setPending(n: number) {
  gatePending = n;
  pendingListeners.forEach((l) => l(gatePending));
}

/** Suscribe al número de peticiones a Yahoo en curso/en cola. Devuelve un cancelador. */
export function onPendingData(listener: (n: number) => void): () => void {
  pendingListeners.add(listener);
  listener(gatePending);
  return () => {
    pendingListeners.delete(listener);
  };
}

function gate<T>(task: () => Promise<T>): Promise<T> {
  setPending(gatePending + 1);
  const run = async (): Promise<T> => {
    gateActive++;
    try {
      return await task();
    } finally {
      gateActive--;
      const next = gateQueue.shift();
      if (next) next();
      setPending(gatePending - 1);
    }
  };
  if (gateActive < MAX_CONCURRENT) return run();
  return new Promise<void>((resolve) => gateQueue.push(resolve)).then(run);
}

export const api = {
  search: (q: string) => req<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}`),

  analysis: (ticker: string) =>
    gate(() => req<Analysis>(`/api/analysis/${ticker}?lang=${currentLang()}`)),

  sentiment: (ticker: string) =>
    gate(() => req<Sentiment>(`/api/sentiment/${ticker}?lang=${currentLang()}`)),

  news: (ticker: string) => req<NewsItem[]>(`/api/news/${ticker}`),

  feed: (ticker: string, offset = 0, limit = 5) =>
    req<{ posts: FeedPost[]; total: number }>(
      `/api/feed/${ticker}?offset=${offset}&limit=${limit}`
    ),
  addFeedPost: (
    ticker: string,
    body: { kind: "x" | "image" | "text"; url?: string; text?: string; image?: string }
  ) => req<FeedPost>(`/api/feed/${ticker}`, { method: "POST", body: JSON.stringify(body) }),
  editFeedPost: (id: number, body: { text?: string; url?: string }) =>
    req<FeedPost>(`/api/feed/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteFeedPost: (id: number) =>
    req<{ deleted: boolean }>(`/api/feed/${id}`, { method: "DELETE" }),

  chart: (ticker: string, period = "1y", interval = "1d", prepost = false) =>
    gate(() =>
      req<ChartBundle>(
        `/api/chart/${ticker}?period=${period}&interval=${interval}&prepost=${prepost}`
      )
    ),
  ema: (
    ticker: string,
    opts: { length: number; tf: string; period: string; interval: string; prepost?: boolean }
  ) =>
    gate(() =>
      req<{ points: LinePoint[] }>(
        `/api/ema/${ticker}?length=${opts.length}&tf=${opts.tf}&period=${opts.period}` +
          `&interval=${opts.interval}&prepost=${opts.prepost ? true : false}`
      )
    ),
  trendlines: (ticker: string, period = "1y", interval = "1d", prepost = false) =>
    gate(() =>
      req<{ lines: TrendLine[] }>(
        `/api/trendlines/${ticker}?period=${period}&interval=${interval}&prepost=${prepost}`
      )
    ),
  price: (ticker: string) =>
    req<{ price: number | null; realtime: boolean }>(`/api/price/${ticker}`),

  lots: (ticker: string) => req<Position>(`/api/lots/${ticker}`),

  addLot: (lot: {
    ticker: string;
    price: number;
    shares: number;
    side: "buy" | "sell";
    date?: string;
    note?: string;
  }) => req<Lot>(`/api/lots`, { method: "POST", body: JSON.stringify(lot) }),

  deleteLot: (id: number) => req<{ deleted: boolean }>(`/api/lots/${id}`, { method: "DELETE" }),

  strategy: (ticker: string) => req<Strategy>(`/api/strategy/${ticker}`, { method: "POST" }),

  portfolio: () => req<Portfolio>(`/api/portfolio`),

  watchlist: () => req<WatchlistItem[]>(`/api/watchlist`),
  watchlistStatus: (ticker: string) =>
    req<{ in_watchlist: boolean }>(`/api/watchlist/status/${ticker}`),
  watchlistAdd: (ticker: string) =>
    req<{ ok: boolean }>(`/api/watchlist/${ticker}`, { method: "POST" }),
  watchlistRemove: (ticker: string) =>
    req<{ ok: boolean }>(`/api/watchlist/${ticker}`, { method: "DELETE" }),

  radarwatch: () => req<WatchlistItem[]>(`/api/radarwatch`),
  radarwatchStatus: (ticker: string) =>
    req<{ in_radar: boolean }>(`/api/radarwatch/status/${ticker}`),
  radarwatchAdd: (ticker: string) =>
    req<{ ok: boolean }>(`/api/radarwatch/${ticker}`, { method: "POST" }),
  radarwatchRemove: (ticker: string) =>
    req<{ ok: boolean }>(`/api/radarwatch/${ticker}`, { method: "DELETE" }),

  alerts: (ticker?: string) => req<Alert[]>(`/api/alerts${ticker ? `?ticker=${ticker}` : ""}`),
  addAlert: (a: { ticker: string; type: string; threshold: number | null; note?: string }) =>
    req<Alert>(`/api/alerts`, { method: "POST", body: JSON.stringify(a) }),
  deleteAlert: (id: number) => req<{ deleted: boolean }>(`/api/alerts/${id}`, { method: "DELETE" }),
  checkAlerts: () => req<{ triggered: TriggeredAlert[] }>(`/api/alerts/check`),
  dismissAlerts: () => req<{ ok: boolean }>(`/api/alerts/dismiss`, { method: "POST" }),

  notificationsStatus: () =>
    req<{ supported: boolean; enabled: boolean }>(`/api/notifications/status`),
  notificationsToggle: (enabled: boolean) =>
    req<{ enabled: boolean }>(`/api/notifications/toggle`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  notificationsTest: () => req<{ sent: boolean }>(`/api/notifications/test`, { method: "POST" }),

  breakoutsRecent: () => req<{ triggered: BreakoutEvent[] }>(`/api/breakouts/recent`),
  breakoutsClear: () => req<{ ok: boolean }>(`/api/breakouts/clear`, { method: "POST" }),
  breakoutsStatus: () => req<BreakoutStatus>(`/api/breakouts/status`),
  breakoutsToggle: (enabled: boolean) =>
    req<{ enabled: boolean }>(`/api/breakouts/toggle`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),

  setups: (ticker: string) => req<SetupAlert[]>(`/api/setups?ticker=${ticker}`),
  createSetup: (body: {
    ticker: string;
    tf: string;
    length: number;
    direction: "long" | "short";
    note?: string;
    lang: string;
  }) => req<SetupAlert>(`/api/setups`, { method: "POST", body: JSON.stringify(body) }),
  toggleSetup: (id: number, active: boolean) =>
    req<{ active: boolean }>(`/api/setups/${id}/toggle`, {
      method: "POST",
      body: JSON.stringify({ active }),
    }),
  deleteSetup: (id: number) => req<{ deleted: boolean }>(`/api/setups/${id}`, { method: "DELETE" }),

  llmStatus: () => req<{ available: boolean; model: string }>(`/api/llm/status`),

  modelsStatus: () => req<ModelsStatus>(`/api/models/status`),

  strategyModules: () => req<StrategyModules>(`/api/strategy/modules?lang=${currentLang()}`),

  radarSources: () =>
    req<{ predefined: RadarSource[]; defaults: RadarConfig }>(
      `/api/radar/sources?lang=${currentLang()}`
    ),
  radarScan: (config: RadarConfig) =>
    req<RadarResult>(`/api/radar?lang=${currentLang()}`, {
      method: "POST",
      body: JSON.stringify(config),
    }),
  radarScoreOne: (ticker: string) =>
    gate(() =>
      req<BreakoutScore>(`/api/radar/score/${ticker}?lang=${currentLang()}`, {
        method: "POST",
      })
    ),
};

/**
 * Lee un endpoint que emite texto en streaming.
 * Si `onMeta` está definido, la primera parte (hasta "\n\n") se interpreta como
 * JSON de metadatos; el resto se va entregando por `onToken`.
 */
export async function streamText(
  url: string,
  options: RequestInit,
  onToken: (text: string) => void,
  onMeta?: (meta: any) => void
): Promise<void> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok || !res.body) {
    let msg = `Error ${res.status}`;
    try {
      const b = await res.json();
      if (b.detail) msg = b.detail;
    } catch {
      /* sin json */
    }
    throw new Error(msg);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let metaDone = !onMeta;
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value, { stream: true });
    if (!metaDone) {
      buffer += text;
      const idx = buffer.indexOf("\n\n");
      if (idx >= 0) {
        try {
          onMeta!(JSON.parse(buffer.slice(0, idx)));
        } catch {
          /* ignora meta mal formada */
        }
        const rest = buffer.slice(idx + 2);
        buffer = "";
        metaDone = true;
        if (rest) onToken(rest);
      }
    } else {
      onToken(text);
    }
  }
}
