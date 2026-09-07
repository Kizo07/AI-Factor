import { useMemo } from 'react';
import { useMantineColorScheme } from '@mantine/core';
import { Alert, SimpleGrid, Skeleton, Stack, Text } from '@mantine/core';
import type Plotly from 'plotly.js';
import PlotChart from '../components/PlotChart';
import SectionTitle from '../components/SectionTitle';
import { quantile } from '../format';
import type { ExposureRow } from '../types';
import { C_ACCENT, C_INFRA, C_THEME } from '../types';

interface DistributionsViewProps {
  valid: ExposureRow[];
  exposureLoading: boolean;
  error: string | null;
}

const DIST_SPECS = [
  {
    col: 'beta_theme' as const,
    title: 'β_theme',
    color: C_THEME,
    caption:
      'How much a stock co-moves with the AI Theme basket after controls. Right of zero: returns amplified by AI sentiment.',
  },
  {
    col: 'beta_infra' as const,
    title: 'β_infra',
    color: C_INFRA,
    caption:
      'Loading on the AI Infrastructure factor (data centers, power, semis capex chain).',
  },
  {
    col: 'exp_combined' as const,
    title: 'Combined exposure E = β_theme·σ(F_theme) + β_infra·σ(F_infra)',
    color: C_ACCENT,
    caption:
      'Vol-scaled exposure: expected daily return contribution per unit of factor movement, comparable across stocks.',
  },
];

export default function DistributionsView({
  valid,
  exposureLoading,
  error,
}: DistributionsViewProps) {
  const dark = useMantineColorScheme().colorScheme !== 'light';
  const histograms = useMemo(
    () =>
      DIST_SPECS.map((spec) => {
        const x = valid.map((r) => r[spec.col]).filter((v): v is number => v !== null);
        const med = x.length ? quantile(x, 0.5) : NaN;
        const p90 = x.length ? quantile(x, 0.9) : NaN;
        return { spec, x, med, p90 };
      }),
    [valid],
  );

  if (exposureLoading) {
    return (
      <Stack>
        <SimpleGrid cols={{ base: 1, lg: 3 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} height={360} radius="md" />
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

  if (valid.length === 0) {
    return <Alert color="yellow">No stocks pass the current filters.</Alert>;
  }

  return (
    <div>
      <Text fz="1.5rem" fw={700}>
        Cross-Sectional Distributions
      </Text>

      <SimpleGrid cols={{ base: 1, lg: 3 }} mt="md">
        {histograms.map(({ spec, x, med, p90 }) => (
          <div key={spec.col}>
            <SectionTitle>{spec.title.split(' E =')[0]}</SectionTitle>
            <PlotChart
              data={[
                {
                  type: 'histogram',
                  x,
                  nbinsx: 40,
                  marker: { color: spec.color, opacity: 0.75 },
                  hovertemplate: '%{x:.3f}: %{y} stocks<extra></extra>',
                } as unknown as Plotly.Data,
              ]}
              height={360}
              layout={{
                showlegend: false,
                xaxis: { title: { text: spec.col } },
                yaxis: { title: { text: '# stocks' } },
                shapes: [
                  {
                    type: 'line',
                    x0: med,
                    x1: med,
                    y0: 0,
                    y1: 1,
                    yref: 'paper',
                    line: { color: dark ? '#edf7fc' : '#445e72', dash: 'dash' },
                  },
                  {
                    type: 'line',
                    x0: p90,
                    x1: p90,
                    y0: 0,
                    y1: 1,
                    yref: 'paper',
                    line: { color: C_ACCENT, dash: 'dot' },
                  },
                ],
                annotations: [
                  {
                    x: med,
                    y: 1,
                    yref: 'paper',
                    text: `median ${med.toFixed(3)}`,
                    showarrow: false,
                    font: { size: 10 },
                  },
                  {
                    x: p90,
                    y: 0.9,
                    yref: 'paper',
                    text: `p90 ${p90.toFixed(3)}`,
                    showarrow: false,
                    font: { size: 10 },
                  },
                ],
              }}
            />
            <Text size="xs" c="dimmed">
              {spec.caption}
            </Text>
          </div>
        ))}
      </SimpleGrid>
    </div>
  );
}