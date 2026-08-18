import type {
  ExposureResponse,
  FactorsResponse,
  Meta,
  Model,
  RecomputeResponse,
  ReturnsResponse,
  RollingBetasResponse,
  TradingDaysResponse,
} from './types';

const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`GET ${path} failed (${res.status}): ${body.slice(0, 300)}`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`POST ${path} failed (${res.status}): ${text.slice(0, 300)}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => get<Meta>('/meta'),
  exposure: (model: Model) => get<ExposureResponse>(`/exposure?model=${model}`),
  recompute: (startDate: string, endDate: string, model: Model) =>
    post<RecomputeResponse>('/exposure/recompute', {
      start_date: startDate,
      end_date: endDate,
      model,
    }),
  factors: () => get<FactorsResponse>('/factors'),
  returns: (ticker: string) =>
    get<ReturnsResponse>(`/returns?ticker=${encodeURIComponent(ticker)}`),
  tradingDays: () => get<TradingDaysResponse>('/trading-days'),
  rollingBetas: (ticker: string, window: number, model: Model) =>
    get<RollingBetasResponse>(
      `/rolling-betas?ticker=${encodeURIComponent(ticker)}&window=${window}&model=${model}`,
    ),
};