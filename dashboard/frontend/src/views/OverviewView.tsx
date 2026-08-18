import { useMemo } from 'react';
import { useMantineColorScheme } from '@mantine/core';
import { Alert, SimpleGrid, Skeleton, Stack, Text } from '@mantine/core';
import type Plotly from 'plotly.js';
import PlotChart from '../components/PlotChart';
import KpiCard from '../components/KpiCard';
import QuadrantCard from '../components/QuadrantCard';
import SectionTitle from '../components/SectionTitle';
import { fmtInt, fmtSigned } from '../format';
import type { ExposureRow, Meta, Model } from '../types';
import {
  C_ACCENT,
  C_GREEN,
  C_INFRA,
  C_THEME,
  MODEL_LABELS,
  QUADRANT_COLORS,
  QUADRANT_ORDER,
  SECTOR_PALETTE,
} from '../types';

interface OverviewViewProps {
  valid: ExposureRow[];
  unestimable: ExposureRow[];
  medTheme: number;
  medInfra: number;
  meta: Meta | null;
  model: Model;
  periodCaption: string;
  exposureLoading: boolean;
  error: string | null;
}

export default function OverviewView({
  valid,
  unestimable,
  medTheme,
  medInfra,
  meta,
  model,
  periodCaption,
  exposureLoading,
  error,
}: OverviewViewProps) {
  const dark = useMantineColorScheme().colorScheme !== 'light';
  const sigShare =
    valid.length > 0
      ? (valid.filter(
          (r) =>
            (r.t_theme !== null && Math.abs(r.t_theme) >= 2) ||
            (r.t_infra !== null && Math.abs(r.t_infra) >= 2),
        ).length /
          valid.length) *
        100
      : 0;
  const nLeaders = valid.filter((r) => r.quadrant === 'AI Leader').length;

  const scatterData = useMemo(() => {
    const sectors = [...new Set(valid.map((r) => r.gics_sector).filter(Boolean))] as string[];
    return sectors.map((sector, i) => {
      const grp = valid.filter((r) => r.gics_sector === sector);
      return {
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: sector,
        x: grp.map((r) => r.beta_theme),
        y: grp.map((r) => r.beta_infra),
        marker: {
          size: grp.map((r) => 6 + 10 * Math.min(1, Math.max(0, r.r2 ?? 0))),
          color: SECTOR_PALETTE[i % SECTOR_PALETTE.length],
          opacity: 0.75,
          line: { width: 0.5, color: dark ? 'rgba(255,255,255,0.25)' : 'rgba(51,65,85,0.25)' },
        },
        customdata: grp.map((r) => [
          r.ticker,
          r.name ?? '',
          r.t_theme,
          r.t_infra,
          r.r2,
          r.quadrant ?? '—',
        ]),
        hovertemplate:
          '<b>%{customdata[0]}</b> — %{customdata[1]}<br>' +
          `Sector: ${sector} · %{customdata[5]}<br>` +
          'β_theme: %{x:.3f} (t=%{customdata[2]:.2f})<br>' +
          'β_infra: %{y:.3f} (t=%{customdata[3]:.2f})<br>' +
          'R²: %{customdata[4]:.2f}<extra></extra>',
      };
    });
  }, [valid]);

  const extremes = useMemo(
    () =>
      [...valid]
        .filter(
          (r) =>
            r.exp_combined !== null && r.beta_theme !== null && r.beta_infra !== null,
        )
        .sort((a, b) => Math.abs(b.exp_combined!) - Math.abs(a.exp_combined!))
        .slice(0, 8),
    [valid],
  );

  const quadrantCards = useMemo(
    () =>
      QUADRANT_ORDER.map((q) => {
        const grp = valid.filter((r) => r.quadrant === q);
        const examples = [...grp]
          .filter((r) => r.exp_combined !== null)
          .sort((a, b) => b.exp_combined! - a.exp_combined!)
          .slice(0, 3)
          .map((r) => r.ticker);
        return {
          title: q,
          count: grp.length,
          examples: examples.length > 0 ? `e.g. ${examples.join(', ')}` : '—',
          accent: QUADRANT_COLORS[q] ?? C_ACCENT,
        };
      }),
    [valid],
  );

  if (exposureLoading) {
    return (
      <Stack>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} height={92} radius="md" />
          ))}
        </SimpleGrid>
        <Skeleton height={560} radius="md" />
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} height={120} radius="md" />
          ))}
        </SimpleGrid>
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

  return (
    <div>
      <Text fz="1.5rem" fw={700}>
        S&P 500 AI Exposure — Overview
      </Text>
      <Text size="sm" c="dimmed" mb="md">
        Model: <b>{MODEL_LABELS[model]}</b> · <b>{periodCaption}</b> ·{' '}
        {valid.length} of {valid.length + unestimable.length} filtered stocks shown
      </Text>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 5 }}>
        <KpiCard
          label="Stocks estimated"
          value={fmtInt(valid.filter((r) => r.beta_theme !== null).length)}
          sub={`of ${meta?.n_stocks_total ?? '—'} constituents`}
          accent={C_ACCENT}
        />
        <KpiCard
          label="Median β_theme"
          value={fmtSigned(medTheme)}
          sub="AI Theme factor loading"
          accent={C_THEME}
        />
        <KpiCard
          label="Median β_infra"
          value={fmtSigned(medInfra)}
          sub="AI Infra factor loading"
          accent={C_INFRA}
        />
        <KpiCard
          label="Significant AI exposure"
          value={`${sigShare.toFixed(1)}%`}
          sub="|t| ≥ 2 on either AI beta (NW HAC)"
          accent={C_GREEN}
        />
        <KpiCard
          label="AI Leaders"
          value={String(nLeaders)}
          sub="both betas above cross-sectional median"
          accent={C_ACCENT}
        />
      </SimpleGrid>

      <SectionTitle>AI Exposure Map — β_theme × β_infra</SectionTitle>
      {valid.length === 0 ? (
        <Alert color="yellow" title="No stocks pass the current filters." />
      ) : (
        <>
          <PlotChart
            data={scatterData}
            height={560}
            layout={{
              xaxis: { title: { text: 'β_theme (AI Theme factor loading)' } },
              yaxis: { title: { text: 'β_infra (AI Infra factor loading)' } },
              shapes: [
                {
                  type: 'line',
                  x0: medTheme,
                  x1: medTheme,
                  y0: 0,
                  y1: 1,
                  yref: 'paper',
                  line: { color: 'rgba(34,211,238,0.5)', dash: 'dash' },
                },
                {
                  type: 'line',
                  x0: 0,
                  x1: 1,
                  xref: 'paper',
                  y0: medInfra,
                  y1: medInfra,
                  line: { color: 'rgba(245,158,11,0.5)', dash: 'dash' },
                },
              ],
              annotations: [
                ...extremes.map((r) => ({
                  x: r.beta_theme as number,
                  y: r.beta_infra as number,
                  text: r.ticker,
                  showarrow: true,
                  arrowhead: 0,
                  arrowsize: 0.6,
                  ax: 0,
                  ay: -22,
                  font: { size: 10, color: dark ? '#e2e8f0' : '#334155' },
                  arrowcolor: 'rgba(226,232,240,0.4)',
                })),
                ...cornerLabels(valid),
              ] as Plotly.Layout['annotations'],
            }}
          />
          <Text size="xs" c="dimmed" mt={4}>
            Bubble size ∝ regression R². Dashed lines are cross-sectional medians
            (quadrant boundaries). Labels mark the largest |vol-scaled combined exposures|.
          </Text>
        </>
      )}

      <SectionTitle>Exposure quadrants</SectionTitle>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        {quadrantCards.map((q) => (
          <QuadrantCard key={q.title} {...q} />
        ))}
      </SimpleGrid>

      {unestimable.length > 0 && (
        <Alert color="blue" mt="md">
          ⚠️ Not estimable in the selected period (too few observations):{' '}
          {unestimable.map((r) => r.ticker).join(', ')}. Excluded from charts.
        </Alert>
      )}
    </div>
  );
}

function cornerLabels(valid: ExposureRow[]): Plotly.Layout['annotations'] {
  const xs = valid.map((r) => r.beta_theme ?? 0);
  const ys = valid.map((r) => r.beta_infra ?? 0);
  const xr: [number, number] = [Math.min(...xs), Math.max(...xs)];
  const yr: [number, number] = [Math.min(...ys), Math.max(...ys)];
  return [
    { x: xr[1], y: yr[1], text: 'AI LEADERS', xanchor: 'right', yanchor: 'top' },
    { x: xr[1], y: yr[0], text: 'THEME PLAYS', xanchor: 'right', yanchor: 'bottom' },
    { x: xr[0], y: yr[1], text: 'INFRA PLAYS', xanchor: 'left', yanchor: 'top' },
    { x: xr[0], y: yr[0], text: 'LOW EXPOSURE', xanchor: 'left', yanchor: 'bottom' },
  ].map((a) => ({
    ...a,
    showarrow: false,
    font: { size: 10, color: 'rgba(148,163,184,0.55)' },
  })) as Plotly.Layout['annotations'];
}