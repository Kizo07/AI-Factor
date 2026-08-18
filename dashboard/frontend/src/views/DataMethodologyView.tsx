import { useMemo } from 'react';
import {
  Alert,
  Badge,
  Button,
  ScrollArea,
  Skeleton,
  Stack,
  Table,
  Text,
} from '@mantine/core';
import { IconDownload } from '@tabler/icons-react';
import SectionTitle from '../components/SectionTitle';
import { downloadCsv, fmtNum, fmtPct, fmtSigned } from '../format';
import type { ExposureRow, Meta, Model } from '../types';

interface DataMethodologyViewProps {
  exposure: ExposureRow[];
  unestimable: ExposureRow[];
  meta: Meta | null;
  model: Model;
  periodCaption: string;
  periodSource: string;
  startDate: string;
  endDate: string;
  exposureLoading: boolean;
  error: string | null;
}

export default function DataMethodologyView({
  exposure,
  unestimable,
  meta,
  model,
  periodCaption,
  periodSource,
  startDate,
  endDate,
  exposureLoading,
  error,
}: DataMethodologyViewProps) {
  const sorted = useMemo(
    () =>
      [...exposure].sort((a, b) => {
        const ae = a.exp_combined ?? -Infinity;
        const be = b.exp_combined ?? -Infinity;
        return be - ae;
      }),
    [exposure],
  );

  if (exposureLoading) {
    return (
      <Stack>
        <Skeleton height={520} radius="md" />
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

  const csvName = `sp500_ai_exposure_${model}_${startDate}_${endDate}.csv`;

  return (
    <div>
      <Text fz="1.5rem" fw={700}>
        Data &amp; Methodology
      </Text>

      <SectionTitle>Full exposure table</SectionTitle>
      <Text size="sm" c="dimmed" mb="sm">
        {periodCaption} · {periodSource}
      </Text>

      <Button
        leftSection={<IconDownload size={16} />}
        mb="sm"
        onClick={() => downloadCsv(csvName, sorted)}
      >
        Download CSV
      </Button>

      <ScrollArea h={520} type="auto">
        <Table striped highlightOnHover withTableBorder stickyHeader>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Ticker</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Sector</Table.Th>
              <Table.Th ta="right">β_theme</Table.Th>
              <Table.Th ta="right">t_theme</Table.Th>
              <Table.Th ta="right">β_infra</Table.Th>
              <Table.Th ta="right">t_infra</Table.Th>
              <Table.Th ta="right">Alpha (ann.)</Table.Th>
              <Table.Th ta="right">R²</Table.Th>
              <Table.Th ta="right">σ(F_theme)</Table.Th>
              <Table.Th ta="right">σ(F_infra)</Table.Th>
              <Table.Th ta="right">E_theme</Table.Th>
              <Table.Th ta="right">E_infra</Table.Th>
              <Table.Th ta="right">E_combined</Table.Th>
              <Table.Th ta="right">pctl β_theme</Table.Th>
              <Table.Th ta="right">pctl β_infra</Table.Th>
              <Table.Th ta="right">pctl E</Table.Th>
              <Table.Th>Quadrant</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sorted.map((r) => (
              <Table.Tr key={r.ticker}>
                <Table.Td>
                  <Badge variant="light" color="theme" size="sm">
                    {r.ticker}
                  </Badge>
                </Table.Td>
                <Table.Td>{r.name ?? '—'}</Table.Td>
                <Table.Td>{r.gics_sector ?? '—'}</Table.Td>
                <Table.Td ta="right">{fmtSigned(r.beta_theme)}</Table.Td>
                <Table.Td ta="right">{fmtNum(r.t_theme)}</Table.Td>
                <Table.Td ta="right">{fmtSigned(r.beta_infra)}</Table.Td>
                <Table.Td ta="right">{fmtNum(r.t_infra)}</Table.Td>
                <Table.Td ta="right">{fmtPct(r.alpha_ann)}</Table.Td>
                <Table.Td ta="right">{fmtNum(r.r2, 3)}</Table.Td>
                <Table.Td ta="right">{fmtNum(r.vol_theme, 4)}</Table.Td>
                <Table.Td ta="right">{fmtNum(r.vol_infra, 4)}</Table.Td>
                <Table.Td ta="right">{fmtSigned(r.exp_theme, 4)}</Table.Td>
                <Table.Td ta="right">{fmtSigned(r.exp_infra, 4)}</Table.Td>
                <Table.Td ta="right" fw={600}>
                  {fmtSigned(r.exp_combined, 4)}
                </Table.Td>
                <Table.Td ta="right">{fmtNum(r.pct_beta_theme, 0)}</Table.Td>
                <Table.Td ta="right">{fmtNum(r.pct_beta_infra, 0)}</Table.Td>
                <Table.Td ta="right">{fmtNum(r.pct_exp_combined, 0)}</Table.Td>
                <Table.Td>{r.quadrant ?? '—'}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </ScrollArea>

      {unestimable.length > 0 && (
        <Text size="xs" c="dimmed" mt={4}>
          Rows with “—”: {unestimable.map((r) => r.ticker).join(', ')} — insufficient valid
          observations in the selected period; betas not estimable.
        </Text>
      )}

      <SectionTitle>Methodology</SectionTitle>
      <Stack gap="xs">
        <Text size="sm">
          <b>Regression.</b> For each S&amp;P 500 stock <i>i</i>, daily OLS over the{' '}
          <b>regression period selected in the sidebar</b> — every trading day in [start,
          end] where all inputs are non-NaN. Default: the trailing{' '}
          <b>{meta?.window ?? 252}-trading-day</b> window (minimum 200 valid observations).
          For custom periods the observation floor adapts to the period length (~75% of the
          available common days, clamped to [40, 200]) so short periods remain estimable:
        </Text>
        <Text size="sm" style={{ fontFamily: 'monospace' }} ta="center">
          r_i,t − rf_t = α_i + β_theme·F_AITheme,t + β_infra·F_AIInfra,t + γ′·Controls_t + ε_i,t
        </Text>
        <Text size="sm">
          <b>Period selector</b> — any start/end within the available data (FF5+UMD ends{' '}
          {meta?.ff_data_through ?? '—'}, Market-only ends {meta?.price_data_through ?? '—'}
          ). The default period loads precomputed estimates instantly; a custom period
          recomputes all ~{meta?.n_stocks_total ?? '—'} Newey–West regressions on the fly
          (≈3 s, then cached per period+model). Periods with fewer than 40 common trading
          days are refused. All cross-sectional tabs and the Deep-Dive regression stats
          reflect the selected period; the Deep-Dive rolling chart keeps its own window
          length.
        </Text>
        <Text size="sm">
          <b>F_AITheme</b> — AUM-weighted basket of AI-theme ETFs, excess over the risk-free
          rate. <b>F_AIInfra</b> — AI-infrastructure ETF factor (data centers, power, semis
          capex chain), excess over rf.
        </Text>
        <Text size="sm">
          <b>Controls</b> — Fama–French 5 factors + momentum (mkt_rf, smb, hml, rmw, cma,
          umd) for the FF5+UMD model; market excess return (SPY − rf) only for the
          Market-only model.
        </Text>
        <Text size="sm">
          <b>Inference</b> — Newey–West (HAC, 5 lags) t-statistics. |t| ≥ 2 ≈ significant at
          5%.
        </Text>
        <Text size="sm">
          <b>Vol-scaled exposure</b> — E = β·σ(F), with σ(F) the daily factor standard
          deviation over the window; E_combined = E_theme + E_infra. Comparable in return
          units across stocks.
        </Text>
        <Text size="sm">
          <b>Quadrants</b> — vs cross-sectional medians of β_theme / β_infra:{' '}
          <b>AI Leader</b> (both above), <b>Theme Play</b> (theme only),{' '}
          <b>Infra Play</b> (infra only), <b>Low Exposure</b> (both below).
        </Text>

        <Text size="sm" fw={600} mt="xs">
          As-of dates
        </Text>
        <Table.ScrollContainer minWidth={400}>
          <Table withTableBorder>
            <Table.Tbody>
              <Table.Tr>
                <Table.Td>Prices / stock returns</Table.Td>
                <Table.Td ta="right">{meta?.price_data_through ?? '—'}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td>AI factors</Table.Td>
                <Table.Td ta="right">{meta?.factor_data_through ?? '—'}</Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td>FF controls</Table.Td>
                <Table.Td ta="right">{meta?.ff_data_through ?? '—'}</Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>

        <Text size="sm">
          Fama–French factors are published with a lag. The FF5+UMD regression therefore
          uses the trailing 252 days of <i>common</i> data (window ends{' '}
          {meta?.ff_data_through ?? '—'}); the Market-only control model is valid through{' '}
          {meta?.price_data_through ?? '—'}.
        </Text>
        <Text size="sm">
          <b>Coverage</b> — {meta?.n_stocks_estimated ?? '—'} of{' '}
          {meta?.n_stocks_total ?? '—'} constituents estimated; 3 recent spin-offs (FDXF,
          HONA, Q) lack 200 observations and are not estimable.
        </Text>
        <Text size="sm" fw={600} mt="xs">
          Limitations
        </Text>
        <Text size="sm">
          · <i>FF publication lag</i> — the primary model cannot use the most recent ~2
          months of returns.
        </Text>
        <Text size="sm">
          · <i>Current-AUM weights</i> — factor baskets reflect today's fund weights, not
          historical composition.
        </Text>
        <Text size="sm">
          · <i>Market-implied ≠ fundamental</i> — betas measure how prices co-move with AI
          factors, not a company's actual AI revenue or strategy; they can reflect sentiment
          and flows.
        </Text>
        <Text size="sm">
          · <i>Spin-offs</i> — FDXF, HONA and Q have insufficient history for a stable
          estimate.
        </Text>
        <Text size="sm">
          · One-year windows are sensitive to regime shifts; rolling betas (Deep Dive tab)
          show stability.
        </Text>
      </Stack>
    </div>
  );
}