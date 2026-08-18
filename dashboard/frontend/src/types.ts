// API data types (mirror the FastAPI backend responses).

export type Model = 'ff' | 'market';

export interface Meta {
  generated_at: string;
  price_data_through: string;
  factor_data_through: string;
  ff_data_through: string;
  window: number;
  n_stocks_total: number;
  n_stocks_estimated: number;
  failed_tickers: string[];
}

export interface ExposureRow {
  ticker: string;
  name: string | null;
  gics_sector: string | null;
  beta_theme: number | null;
  t_theme: number | null;
  beta_infra: number | null;
  t_infra: number | null;
  alpha_ann: number | null;
  r2: number | null;
  n_obs: number | null;
  window_end: string | null;
  vol_theme: number | null;
  vol_infra: number | null;
  exp_theme: number | null;
  exp_infra: number | null;
  exp_combined: number | null;
  pct_beta_theme: number | null;
  pct_beta_infra: number | null;
  pct_exp_combined: number | null;
  quadrant: string | null;
}

export interface FactorRow {
  date: string;
  ai_theme_excess_return: number | null;
  ai_infra_excess_return: number | null;
  rf_rate: number | null;
}

export interface ReturnRow {
  date: string;
  return: number | null;
}

export interface RollingBetaRow {
  date: string;
  beta_theme: number;
  beta_infra: number;
}

export interface ConstituentRow {
  ticker: string;
  name: string;
  gics_sector: string;
}

export interface ExposureResponse {
  model: Model;
  rows: ExposureRow[];
}

export interface RecomputeResponse {
  model: Model;
  start_date: string;
  end_date: string;
  rows: ExposureRow[];
}

export interface RollingBetasResponse {
  ticker: string;
  window: number;
  model: Model;
  rows: RollingBetaRow[];
}

export interface ReturnsResponse {
  ticker: string;
  rows: ReturnRow[];
}

export interface FactorsResponse {
  rows: FactorRow[];
}

export interface TradingDaysResponse {
  days: string[];
}

export const MODEL_LABELS: Record<Model, string> = {
  ff: 'FF5+UMD (through FF publication date)',
  market: 'Market-only (through yesterday)',
};

export const QUADRANT_ORDER = [
  'AI Leader',
  'Theme Play',
  'Infra Play',
  'Low Exposure',
] as const;

export const QUADRANT_COLORS: Record<string, string> = {
  'AI Leader': '#a78bfa',
  'Theme Play': '#22d3ee',
  'Infra Play': '#f59e0b',
  'Low Exposure': '#64748b',
};

export const SECTOR_PALETTE = [
  '#22d3ee',
  '#a78bfa',
  '#f59e0b',
  '#34d399',
  '#f87171',
  '#60a5fa',
  '#f472b6',
  '#facc15',
  '#4ade80',
  '#c084fc',
  '#fb923c',
  '#94a3b8',
];

export const C_THEME = '#22d3ee';
export const C_INFRA = '#f59e0b';
export const C_ACCENT = '#a78bfa';
export const C_GREEN = '#34d399';
export const C_RED = '#f87171';
export const C_GRAY = '#64748b';