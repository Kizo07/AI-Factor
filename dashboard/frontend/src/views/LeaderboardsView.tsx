import { useMemo, useState } from 'react';
import { Alert, SimpleGrid, Slider, Skeleton, Stack, Text } from '@mantine/core';
import PlotChart from '../components/PlotChart';
import SectionTitle from '../components/SectionTitle';
import { sigStar } from '../format';
import type { ExposureRow } from '../types';
import { C_ACCENT, C_INFRA, C_RED, C_THEME } from '../types';

interface LeaderboardsViewProps {
  valid: ExposureRow[];
  exposureLoading: boolean;
  error: string | null;
}

interface BoardSpec {
  col: 'beta_theme' | 'beta_infra' | 'exp_combined';
  tCol: 't_theme' | 't_infra' | null;
  title: string;
  color: string;
}

const LB_SPECS: BoardSpec[] = [
  { col: 'beta_theme', tCol: 't_theme', title: 'β_theme', color: C_THEME },
  { col: 'beta_infra', tCol: 't_infra', title: 'β_infra', color: C_INFRA },
  {
    col: 'exp_combined',
    tCol: null,
    title: 'Combined vol-scaled exposure E = Σβ·σ(F)',
    color: C_ACCENT,
  },
];

export default function LeaderboardsView({
  valid,
  exposureLoading,
  error,
}: LeaderboardsViewProps) {
  const [n, setN] = useState(15);

  const boards = useMemo(
    () =>
      LB_SPECS.map((spec) => {
        const withVal = valid.filter((r) => r[spec.col] !== null);
        const top = [...withVal].sort((a, b) => b[spec.col]! - a[spec.col]!).slice(0, n);
        const bot = [...withVal].sort((a, b) => a[spec.col]! - b[spec.col]!).slice(0, n);
        const seen = new Set<string>();
        const board = [...top, ...bot].filter((r) => {
          if (seen.has(r.ticker)) return false;
          seen.add(r.ticker);
          return true;
        });
        board.sort((a, b) => a[spec.col]! - b[spec.col]!);
        return { spec, board };
      }),
    [valid, n],
  );

  if (exposureLoading) {
    return (
      <Stack>
        <Skeleton height={40} width={200} radius="md" />
        <SimpleGrid cols={{ base: 1, lg: 3 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} height={640} radius="md" />
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
        Leaderboards
      </Text>
      <Text size="sm" fw={500} mt="md" mb={4}>
        Top / bottom N
      </Text>
      <Slider
        aria-label="Top / bottom N"
        value={n}
        onChange={setN}
        min={5}
        max={30}
        step={1}
        label={(v) => `${v}`}
        w={{ base: '100%', sm: 300 }}
      />

      <SimpleGrid cols={{ base: 1, lg: 3 }} mt="md">
        {boards.map(({ spec, board }) => (
          <div key={spec.col}>
            <SectionTitle>{spec.title}</SectionTitle>
            {valid.length === 0 ? (
              <Alert color="yellow">No data under current filters.</Alert>
            ) : (
              <>
                <PlotChart
                  data={[
                    {
                      type: 'bar',
                      orientation: 'h',
                      x: board.map((r) => r[spec.col]),
                      y: board.map((r) => r.ticker + (spec.tCol ? sigStar(r[spec.tCol]) : Math.abs(r.t_theme ?? 0) >= 2 || Math.abs(r.t_infra ?? 0) >= 2 ? '*' : '')),
                      marker: {
                        color: board.map((r) => ((r[spec.col] ?? 0) >= 0 ? spec.color : C_RED)),
                        opacity: 0.85,
                      },
                      customdata: board.map((r) => [r.name ?? '', r[spec.col]]),
                      hovertemplate:
                        '<b>%{y}</b> %{customdata[0]}<br>' +
                        `${spec.col}: %{x:.4f}<extra></extra>`,
                    },
                  ]}
                  height={640}
                  layout={{
                    showlegend: false,
                    xaxis: { zeroline: true, zerolinecolor: 'rgba(148,163,184,0.5)' },
                    yaxis: { automargin: true },
                  }}
                />
                <Text size="xs" c="dimmed">
                  {spec.tCol ? '*|t| ≥ 2 (significant)' : '*significant on either AI beta'}
                </Text>
              </>
            )}
          </div>
        ))}
      </SimpleGrid>
    </div>
  );
}