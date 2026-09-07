import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Group,
  Loader,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { api } from '../api';
import PlotChart from '../components/PlotChart';
import KpiCard from '../components/KpiCard';
import SectionTitle from '../components/SectionTitle';
import { fmtDate, fmtNum, fmtPct, fmtSigned } from '../format';
import type {
  ExposureRow,
  FactorRow,
  Model,
  ReturnRow,
  RollingBetaRow,
} from '../types';
import {
  C_ACCENT,
  C_GREEN,
  C_INFRA,
  C_THEME,
  QUADRANT_COLORS,
} from '../types';

interface DeepDiveViewProps {
  exposure: ExposureRow[];
  factors: FactorRow[];
  model: Model;
  windowLen: number;
  periodCaption: string;
  exposureLoading: boolean;
  error: string | null;
}

export default function DeepDiveView({
  exposure,
  factors,
  model,
  windowLen,
  periodCaption,
  exposureLoading,
  error,
}: DeepDiveViewProps) {
  const tickers = useMemo(
    () => [...new Set(exposure.map((r) => r.ticker))].sort(),
    [exposure],
  );
  const [ticker, setTicker] = useState<string>('NVDA');
  const [rolling, setRolling] = useState<RollingBetaRow[] | null>(null);
  const [rollingLoading, setRollingLoading] = useState(false);
  const [returns, setReturns] = useState<ReturnRow[] | null>(null);
  const [returnsLoading, setReturnsLoading] = useState(false);
  const [fetchFailed, setFetchFailed] = useState(false);

  const row = useMemo(
    () => exposure.find((r) => r.ticker === ticker),
    [exposure, ticker],
  );

  // Reset to NVDA when the ticker list changes (new period/model).
  useEffect(() => {
    if (tickers.length > 0 && !tickers.includes(ticker)) {
      setTicker(tickers.includes('NVDA') ? 'NVDA' : tickers[0]);
    }
  }, [tickers, ticker]);

  // Fetch rolling betas + returns for the selected stock.
  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setRollingLoading(true);
    setReturnsLoading(true);
    setRolling(null);
    setReturns(null);
    setFetchFailed(false);
    api
      .rollingBetas(ticker, windowLen, model)
      .then((res) => {
        if (!cancelled) setRolling(res.rows);
      })
      .catch((e) => {
        if (!cancelled) {
          setFetchFailed(true);
          notifications.show({ title: 'Rolling betas failed', message: String(e), color: 'red' });
        }
      })
      .finally(() => {
        if (!cancelled) setRollingLoading(false);
      });
    api
      .returns(ticker)
      .then((res) => {
        if (!cancelled) setReturns(res.rows);
      })
      .catch((e) => {
        if (!cancelled) {
          setFetchFailed(true);
          notifications.show({ title: 'Returns failed', message: String(e), color: 'red' });
        }
      })
      .finally(() => {
        if (!cancelled) setReturnsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker, windowLen, model]);

  // --- price vs AI Theme factor (growth of $1) ---------------------------
  const priceChart = useMemo(() => {
    if (!returns || returns.length === 0) return null;
    const retByDate = new Map(returns.map((r) => [r.date.slice(0, 10), r.return]));
    const merged: { date: string; stock: number; theme: number }[] = [];
    for (const f of factors) {
      const d = f.date.slice(0, 10);
      const ret = retByDate.get(d);
      if (ret === undefined || ret === null) continue;
      if (f.ai_theme_excess_return === null || f.rf_rate === null) continue;
      merged.push({
        date: d,
        stock: ret,
        theme: f.ai_theme_excess_return + f.rf_rate,
      });
    }
    if (merged.length === 0) return null;
    let stockG = 1;
    let themeG = 1;
    const stockSeries: number[] = [];
    const themeSeries: number[] = [];
    for (const m of merged) {
      stockG *= 1 + m.stock;
      themeG *= 1 + m.theme;
      stockSeries.push(stockG);
      themeSeries.push(themeG);
    }
    return {
      dates: merged.map((m) => m.date),
      stock: stockSeries,
      theme: themeSeries,
    };
  }, [returns, factors]);

  // --- sector peers ------------------------------------------------------
  const peers = useMemo(() => {
    if (!row?.gics_sector) return [];
    return exposure
      .filter((r) => r.gics_sector === row.gics_sector && r.exp_combined !== null)
      .sort((a, b) => b.exp_combined! - a.exp_combined!);
  }, [exposure, row]);

  if (exposureLoading) {
    return (
      <Stack>
        <Skeleton height={40} width={300} radius="md" />
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} height={92} radius="md" />
          ))}
        </SimpleGrid>
        <Skeleton height={380} radius="md" />
        <Skeleton height={360} radius="md" />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert color="red" title="Failed to load data">
        {error}
      </Alert>
    );
  }

  if (!row) {
    return <Alert color="yellow">No stock selected.</Alert>;
  }

  const notEstimable = row.beta_theme === null;

  return (
    <div>
      <Text fz="1.5rem" fw={700}>
        Stock Deep Dive
      </Text>

      <Select
        label="Select a stock"
        data={tickers.map((t) => {
          const r = exposure.find((x) => x.ticker === t);
          return { value: t, label: r ? `${t} — ${r.name ?? ''}` : t };
        })}
        value={ticker}
        onChange={(v) => v && setTicker(v)}
        searchable
        nothingFoundMessage="No ticker found"
        maxDropdownHeight={300}
        mt="md"
        w={{ base: '100%', sm: 420 }}
      />

      {notEstimable ? (
        <Alert color="yellow" mt="md">
          <b>
            {ticker} ({row.name})
          </b>{' '}
          could not be estimated for the selected period — only {row.n_obs ?? 0} valid
          observations (below the minimum required for a stable regression).
        </Alert>
      ) : (
        <>
          <SectionTitle>
            {row.name} ({ticker}) — {row.gics_sector}
          </SectionTitle>
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }}>
            <KpiCard
              label="Quadrant"
              value={row.quadrant ?? '—'}
              sub="vs cross-sectional medians"
              accent={QUADRANT_COLORS[row.quadrant ?? ''] ?? C_ACCENT}
            />
            <KpiCard
              label="β_theme"
              value={fmtSigned(row.beta_theme)}
              sub={`t = ${fmtNum(row.t_theme)} · pctl ${fmtNum(row.pct_beta_theme, 0)}`}
              accent={C_THEME}
            />
            <KpiCard
              label="β_infra"
              value={fmtSigned(row.beta_infra)}
              sub={`t = ${fmtNum(row.t_infra)} · pctl ${fmtNum(row.pct_beta_infra, 0)}`}
              accent={C_INFRA}
            />
            <KpiCard
              label="Combined exposure"
              value={fmtSigned(row.exp_combined, 4)}
              sub={`E = Σβ·σ(F) · pctl ${fmtNum(row.pct_exp_combined, 0)}`}
              accent={C_ACCENT}
            />
            <KpiCard
              label="Alpha (ann.)"
              value={fmtPct(row.alpha_ann)}
              sub={`R² = ${fmtNum(row.r2)}`}
              accent={C_GREEN}
            />
          </SimpleGrid>

          <SectionTitle>
            Rolling {windowLen}d AI betas — {model === 'ff' ? 'FF5+UMD' : 'Market-only'} model
          </SectionTitle>
          {rollingLoading ? (
            <Group gap="xs" mt="md">
              <Loader size="sm" /> Computing rolling betas…
            </Group>
          ) : rolling && rolling.length > 0 ? (
            <>
              <PlotChart
                data={[
                  {
                    type: 'scatter',
                    mode: 'lines',
                    x: rolling.map((r) => r.date),
                    y: rolling.map((r) => r.beta_theme),
                    name: 'β_theme',
                    line: { color: C_THEME, width: 2 },
                    hovertemplate: '%{x|%Y-%m-%d}<br>β_theme: %{y:.3f}<extra></extra>',
                  },
                  {
                    type: 'scatter',
                    mode: 'lines',
                    x: rolling.map((r) => r.date),
                    y: rolling.map((r) => r.beta_infra),
                    name: 'β_infra',
                    line: { color: C_INFRA, width: 2 },
                    hovertemplate: '%{x|%Y-%m-%d}<br>β_infra: %{y:.3f}<extra></extra>',
                  },
                ]}
                height={380}
                layout={{
                  yaxis: { title: { text: 'Rolling beta' } },
                  shapes: [
                    {
                      type: 'rect',
                      x0: 0,
                      x1: 1,
                      xref: 'paper',
                      y0: -0.05,
                      y1: 0.05,
                      fillcolor: 'rgba(129,154,170,0.10)',
                      line: { width: 0 },
                    },
                    {
                      type: 'line',
                      x0: 0,
                      x1: 1,
                      xref: 'paper',
                      y0: 0,
                      y1: 0,
                      line: { color: 'rgba(129,154,170,0.55)' },
                    },
                  ],
                }}
              />
              <Text size="xs" c="dimmed">
                The rolling chart uses its own window length (sidebar selector) and is
                independent of the regression period above.
              </Text>
            </>
          ) : fetchFailed ? (
            <Alert color="red" mt="md">
              Rolling-betas request failed — see the error notification.
            </Alert>
          ) : (
            <Alert color="blue" mt="md">
              Not enough history for a {windowLen}-day rolling window on {ticker}.
            </Alert>
          )}

          <SectionTitle>Stock vs AI Theme factor (normalized, growth of $1)</SectionTitle>
          {returnsLoading ? (
            <Group gap="xs" mt="md">
              <Loader size="sm" /> Loading price history…
            </Group>
          ) : priceChart ? (
            <>
              <PlotChart
                data={[
                  {
                    type: 'scatter',
                    mode: 'lines',
                    x: priceChart.dates,
                    y: priceChart.stock,
                    name: `${ticker} (total return)`,
                    line: { color: C_ACCENT, width: 2 },
                    hovertemplate: '%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>',
                  },
                  {
                    type: 'scatter',
                    mode: 'lines',
                    x: priceChart.dates,
                    y: priceChart.theme,
                    name: 'AI Theme factor (incl. rf)',
                    line: { color: C_THEME, width: 2 },
                    hovertemplate: '%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>',
                  },
                ]}
                height={360}
                layout={{ yaxis: { title: { text: 'Growth of $1' } } }}
              />
              <Text size="xs" c="dimmed">
                AI Theme is a long–short AUM-weighted basket excess return; the risk-free
                leg is added back for a comparable growth-of-$1 basis.
              </Text>
            </>
          ) : fetchFailed ? (
            <Alert color="red" mt="md">
              Price/factor data request failed — see the error notification.
            </Alert>
          ) : (
            <Alert color="blue" mt="md">
              No overlapping price/factor history.
            </Alert>
          )}

          <SectionTitle>Regression statistics ({periodCaption})</SectionTitle>
          <Table.ScrollContainer minWidth={420}>
            <Table striped withTableBorder w={{ base: '100%', sm: 420 }}>
              <Table.Tbody>
                {[
                  ['β_theme', fmtSigned(row.beta_theme, 4)],
                  ['t(β_theme)', fmtNum(row.t_theme)],
                  ['β_infra', fmtSigned(row.beta_infra, 4)],
                  ['t(β_infra)', fmtNum(row.t_infra)],
                  ['Alpha (annualized)', fmtPct(row.alpha_ann)],
                  ['R²', fmtNum(row.r2, 3)],
                  ['Observations', String(row.n_obs ?? '—')],
                  ['Window end', fmtDate(row.window_end)],
                  ['σ(F_theme) daily', fmtNum(row.vol_theme, 4)],
                  ['σ(F_infra) daily', fmtNum(row.vol_infra, 4)],
                  ['E_theme = β·σ', fmtSigned(row.exp_theme, 4)],
                  ['E_infra = β·σ', fmtSigned(row.exp_infra, 4)],
                  ['E_combined', fmtSigned(row.exp_combined, 4)],
                ].map(([k, v]) => (
                  <Table.Tr key={k}>
                    <Table.Td>{k}</Table.Td>
                    <Table.Td ta="right">{v}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>

          <SectionTitle>Sector peers — {row.gics_sector} (by combined exposure)</SectionTitle>
          <Table.ScrollContainer minWidth={700}>
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Ticker</Table.Th>
                  <Table.Th>Name</Table.Th>
                  <Table.Th ta="right">β_theme</Table.Th>
                  <Table.Th ta="right">β_infra</Table.Th>
                  <Table.Th ta="right">E_combined</Table.Th>
                  <Table.Th>Quadrant</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {peers.map((p) => (
                  <Table.Tr
                    key={p.ticker}
                    style={
                      p.ticker === ticker
                        ? { backgroundColor: 'rgba(167,139,250,0.25)' }
                        : undefined
                    }
                  >
                    <Table.Td>
                      <Group gap={6}>
                        {p.ticker}
                        {p.ticker === ticker && <Badge size="xs" color="accent">selected</Badge>}
                      </Group>
                    </Table.Td>
                    <Table.Td>{p.name ?? '—'}</Table.Td>
                    <Table.Td ta="right">{fmtSigned(p.beta_theme)}</Table.Td>
                    <Table.Td ta="right">{fmtSigned(p.beta_infra)}</Table.Td>
                    <Table.Td ta="right">{fmtSigned(p.exp_combined, 4)}</Table.Td>
                    <Table.Td>{p.quadrant ?? '—'}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </>
      )}
    </div>
  );
}