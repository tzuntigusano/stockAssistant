export interface Quote {
  symbol: string;
  name: string;
  price: number | null;
  previous_close: number | null;
  change?: number;
  change_pct?: number;
  day_high: number | null;
  day_low: number | null;
  open: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  eps: number | null;
  dividend_yield: number | null;
  fifty_two_high: number | null;
  fifty_two_low: number | null;
  currency: string;
  sector?: string | null;
  exchange?: string | null;
}

export interface Indicators {
  ok: boolean;
  price?: number;
  ema20?: number | null;
  ema50?: number | null;
  ema200?: number | null;
  rsi14?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  macd_hist?: number | null;
  atr14?: number | null;
  atr_pct?: number | null;
  change_1d?: number | null;
  change_5d?: number | null;
  change_20d?: number | null;
  high_52w?: number | null;
  low_52w?: number | null;
  support?: number | null;
  resistance?: number | null;
}

export interface Signal {
  text: string;
  bias: "alcista" | "bajista";
  weight: number;
}

export interface Verdict {
  score: number;
  label: string;
  signals: Signal[];
}

export interface Analysis {
  quote: Quote;
  indicators: Indicators;
  verdict: Verdict;
}

export interface Lot {
  id: number;
  ticker: string;
  side: "buy" | "sell";
  date: string;
  price: number;
  shares: number;
  note: string;
  pnl?: number;
  pnl_pct?: number;
  realized?: number;
  realized_pct?: number | null;
}

export interface Position {
  has_position: boolean;
  lots: Lot[];
  realized_pnl: number;
  total_shares?: number;
  total_cost?: number;
  avg_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  current_price?: number;
}

export interface PortfolioItem {
  ticker: string;
  name: string;
  price: number | null;
  currency: string;
  change_pct?: number;
  has_position: boolean;
  realized_pnl: number;
  shares?: number;
  avg_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
}

export interface Portfolio {
  items: PortfolioItem[];
  totals: {
    market_value: number;
    cost: number;
    unrealized_pnl: number;
    unrealized_pnl_pct: number;
    realized_pnl: number;
  };
}

export interface WatchlistItem {
  ticker: string;
  name: string;
  price: number | null;
  currency: string;
  change_pct?: number;
}

export interface TfSentiment {
  verdict: Verdict;
  rsi?: number | null;
  price?: number | null;
  error?: string;
}

export interface Sentiment {
  "1h": TfSentiment;
  "4h": TfSentiment;
  "1d": TfSentiment;
}

export interface Alert {
  id: number;
  ticker: string;
  type: string;
  threshold: number | null;
  note: string;
  active: boolean;
  label: string;
}

export interface TriggeredAlert {
  id: number;
  ticker: string;
  label: string;
  message: string;
  note: string;
}

export interface BreakoutEvent {
  ticker: string;
  price: number;
  resistance: number;
  rvol: number;
  at: string;
  message: string;
}

export interface BreakoutStatus {
  enabled: boolean;
  interval: number;
  realtime: boolean;
  provider: string;
  market_open: boolean;
  watchlist: string[];
}

export interface RadarCandidate {
  ticker: string;
  name: string;
  price: number;
  change_pct: number | null;
  score: number;
  passed: string[];
  rsi: number | null;
  adx: number | null;
  vol_ratio: number | null;
  rel_strength: number | null;
  atr_pct: number | null;
}

export interface RadarResult {
  candidates: RadarCandidate[];
  scanned: number;
  matched: number;
  benchmark: string;
  benchmark_return: number;
}

export interface RadarSource {
  key: string;
  label: string;
}

export type ChartTime = string | number;

export interface CandlePoint {
  time: ChartTime;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface LinePoint {
  time: ChartTime;
  value: number;
}

export interface ElliottCount {
  found: boolean;
  pattern?: "impulse_up" | "impulse_down" | "abc";
  up?: boolean;
  current_wave?: number;
  completed_waves?: number;
  confidence?: number;
  rules?: Record<string, boolean>;
  threshold?: number;
  points?: LinePoint[];
  labels?: { time: ChartTime; value: number; text: string; kind: string }[];
  fibs?: { label: string; price: number }[];
}

export interface TrendLine {
  kind: "support" | "resistance";
  touches: number;
  points: LinePoint[];
  anchors: { t: number; p: number }[]; // timestamps absolutos, para congelar en una alerta
}

export interface VolumePoint {
  time: ChartTime;
  value: number;
  up: boolean;
}

export interface ChartBundle {
  candles: CandlePoint[];
  volume: VolumePoint[];
  rsi: LinePoint[];
  bb_upper: LinePoint[];
  bb_lower: LinePoint[];
  support: number | null;
  resistance: number | null;
}

export interface GeminiModel {
  id: string;
  label: string;
}

export interface ModelsStatus {
  gemini_available: boolean;
  ollama_available: boolean;
  model: string;
  models: GeminiModel[];
}

export interface ModuleOption {
  key: string;
  label: string;
  text: string;
}

export interface StrategyModule {
  label: string;
  default: string;
  options: ModuleOption[];
}

export interface StrategyModules {
  order: string[];
  modules: Record<string, StrategyModule>;
  template: string;
}

// Comando que la IA del chat puede enviar al gráfico (estado completo deseado).
export interface ChartCommand {
  interval?: string;
  emas?: { length: number; tf?: string }[];
  indicators?: string[];
}

export interface BreakoutCheck {
  label: string;
  passed: boolean;
}

export interface BreakoutScore {
  ok: boolean;
  ticker: string;
  name?: string;
  price?: number;
  score?: number;
  checklist?: BreakoutCheck[];
  rsi?: number | null;
  adx?: number | null;
  vol_ratio?: number | null;
  rel_strength?: number | null;
  atr_pct?: number | null;
  benchmark?: string;
  benchmark_return?: number;
}

export interface RadarConfig {
  sources: { predefined: string[]; watchlist: boolean; custom: string[] };
  per_source: number;
  max_universe: number;
  weights: Record<string, number>;
  params: Record<string, number | string>;
  min_score: number;
  max_results: number;
}

export interface Levels {
  support?: number | null;
  resistance?: number | null;
  ema50?: number | null;
  suggested_stop?: number;
  atr14?: number;
  avg_cost?: number;
  breakeven?: number;
}

export interface Strategy {
  verdict: Verdict;
  levels: Levels;
  position: Position;
  narrative: string | null;
  llm_error: string | null;
  context: string;
}

export interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

export interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  published_at: string;
  summary: string;
}

export interface FeedPost {
  id: number;
  ticker: string;
  kind: "x" | "image" | "text";
  url: string | null;
  text: string | null;
  image: string | null; // nombre de fichero servido por /api/feed/image/{name}
  created_at: number; // epoch segundos
}

// --- Carteras ficticias (paper trading) ---
export type PaperMode = "normal" | "fast";

export interface PaperPosition {
  id: number;
  mode: PaperMode;
  ticker: string;
  name: string;
  side: "long" | "short";
  shares: number;
  entry_price: number;
  entry_at: number;
  stop: number;
  initial_stop: number;
  target: number;
  rr: number;
  horizon: string;
  horizon_label?: string;
  thesis: string;
  score: number;
  stop_moved: boolean;
  runner: boolean; // superó el objetivo y se dejó correr (cartera rápida)
  status: "open" | "closed";
  // Solo en abiertas
  current_price?: number | null;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  days_held?: number;
  // Solo en cerradas
  exit_price?: number | null;
  exit_at?: number | null;
  exit_reason?: string;
  exit_reason_label?: string;
  exit_text?: string;
  pnl?: number;
  pnl_pct?: number;
}

export interface PaperPortfolio {
  mode: PaperMode;
  cash: number;
  initial_cash: number;
  equity: number;
  total_pnl: number;
  total_pnl_pct: number;
  realized_pnl: number;
  open_positions: PaperPosition[];
  closed_positions: PaperPosition[];
  trades: number;
  wins: number;
  win_rate: number | null;
  config: {
    risk_pct: number;
    max_positions: number;
    min_score: number;
    horizon: string;
    horizon_label: string;
    max_hold_days: number;
  };
}

export interface PaperCompare {
  portfolios: Record<PaperMode, PaperPortfolio>;
  market_open: boolean;
  leader: PaperMode;
}

export interface PaperLogEntry {
  id: number;
  mode: PaperMode;
  at: number;
  kind: "entry" | "exit" | "stop" | "skip" | "cycle" | "system";
  ticker: string;
  text: string;
}

export interface PaperStatus {
  enabled: boolean;
  running: boolean;
  market_open: boolean;
  last_run: number | null;
  interval: number;
  ny_time: string;
}

export interface SetupAlert {
  id: number;
  ticker: string;
  level_type: string; // 'ema' | 'trendline'
  length: number;
  tf: string; // '15m' | '1h' | '4h' | '1d' | '1wk'
  direction: "long" | "short";
  state: "armed" | "broken" | "retest" | "confirmed";
  note: string;
  active: boolean;
  created_at: number;
  updated_at: number;
  line: { t: number; p: number }[] | null;
}
