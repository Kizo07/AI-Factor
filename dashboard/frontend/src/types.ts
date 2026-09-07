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

// Quadrant + chart colors: Cyan Ledger values (from Kizo07.github.io
// fusion/cyan-ledger), chosen to stay legible on both midnight and ice
// surfaces since plotly trace colors are scheme-blind.
export const QUADRANT_COLORS: Record<string, string> = {
  'AI Leader': '#3fbfae',
  'Theme Play': '#08bfff',
  'Infra Play': '#cf9440',
  'Low Exposure': '#819aaa',
};

export const SECTOR_PALETTE = [
  '#08bfff',
  '#e3ac55',
  '#68dfcf',
  '#f58ba4',
  '#a0e8ff',
  '#cf9440',
  '#3fbfae',
  '#e66785',
  '#6bdbff',
  '#8f621f',
  '#137665',
  '#819aaa',
];

export const C_THEME = '#08bfff';
export const C_INFRA = '#cf9440';
export const C_ACCENT = '#3fbfae';
export const C_GREEN = '#3fbfae';
export const C_RED = '#e66785';
export const C_GRAY = '#819aaa';