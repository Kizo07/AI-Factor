import { useMemo } from 'react';
import { Alert, Skeleton, Stack, Table, Text } from '@mantine/core';
import PlotChart from '../components/PlotChart';
import SectionTitle from '../components/SectionTitle';
import { fmtNum, fmtSigned } from '../format';
import type { ExposureRow } from '../types';
import { C_ACCENT, C_INFRA, C_THEME } from '../types';

interface SectorViewProps {
  valid: ExposureRow[];
  exposureLoading: boolean;
  error: string | null;
}

interface SectorAgg {
  sector: string;
  n: number;
  medTheme: number;
  medInfra: number;
  medR2: number;
  medExp: number;
  pctSig: number;
  leaders: number;
}

export default function SectorView({ valid, exposureLoading, error }: SectorViewProps) {
  const sectors = useMemo<SectorAgg[]>(() => {
    const bySector = new Map<string, ExposureRow[]>();
    for (const r of valid) {
      if (!r.gics_sector) continue;
      const arr = bySector.get(r.gics_sector) ?? [];
      arr.push(r);
      bySector.set(r.gics_sector, arr);
    }
    const agg: SectorAgg[] = [];
    for (const [sector, rows] of bySector) {
      const bt = rows.map((r) => r.beta_theme as number);
      const bi = rows.map((r) => r.beta_infra as number);
      const r2 = rows.map((r) => r.r2 as number);
      const ex = rows.map((r) => r.exp_combined as number);
      const sig = rows.filter(
        (r) =>
          (r.t_theme !== null && Math.abs(r.t_theme) >= 2) ||
          (r.t_infra !== null && Math.abs(r.t_infra) >= 2),
      ).length;
      const leaders = rows.filter((r) => r.quadrant === 'AI Leader').length;
      agg.push({
        sector,
        n: rows.length,
        medTheme: median(bt),
        medInfra: median(bi),
        medR2: median(r2),
        medExp: median(ex),
        pctSig: (sig / rows.length) * 100,
        leaders,
      });
    }
    return agg.sort((a, b) => a.medTheme - b.medTheme);
  }, [valid]);

  if (exposureLoading) {
    return (
      <Stack>
        <Skeleton height={460} radius="md" />
        <Skeleton height={380} radius="md" />
        <Skeleton height={300} radius="md" />
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

  const barData = [
    {
      type: 'bar' as const,
      y: sectors.map((s) => s.sector),
      x: sectors.map((s) => s.medTheme),
      name: 'β_theme',
      orientation: 'h' as const,
      marker: { color: C_THEME, opacity: 0.9 },
      hovertemplate: '%{y}<br>median β_theme: %{x:.3f}<extra></extra>',
    },
    {
      type: 'bar' as const,
      y: sectors.map((s) => s.sector),
      x: sectors.map((s) => s.medInfra),
      name: 'β_infra',
      orientation: 'h' as const,
      marker: { color: C_INFRA, opacity: 0.9 },
      hovertemplate: '%{y}<br>median β_infra: %{x:.3f}<extra></extra>',
    },
  ];

  const leaderData = [
    {
      type: 'bar' as const,
      x: sectors.map((s) => s.sector),
      y: sectors.map((s) => s.leaders),
      marker: { color: C_ACCENT, opacity: 0.9 },
      text: sectors.map((s) => String(s.leaders)),
      textposition: 'outside' as const,
      hovertemplate: '%{x}<br>AI Leaders: %{y}<extra></extra>',
    },
  ];

  return (
    <div>
      <Text fz="1.5rem" fw={700}>
        Sector Analysis
      </Text>

      <SectionTitle>Median AI betas by GICS sector</SectionTitle>
      <PlotChart
        data={barData}
        height={460}
        layout={{
          barmode: 'group',
          xaxis: { title: { text: 'Median beta' } },
          yaxis: { automargin: true },
        }}
      />

      <SectionTitle>AI Leaders per sector</SectionTitle>
      <PlotChart
        data={leaderData}
        height={380}
        layout={{
          yaxis: { title: { text: '# AI Leader stocks' } },
          xaxis: { automargin: true },
        }}
      />

      <SectionTitle>Sector summary table</SectionTitle>
      <Table.ScrollContainer minWidth={700}>
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Sector</Table.Th>
              <Table.Th ta="right">Stocks</Table.Th>
              <Table.Th ta="right">Median β_theme</Table.Th>
              <Table.Th ta="right">Median β_infra</Table.Th>
              <Table.Th ta="right">Median E_combined</Table.Th>
              <Table.Th ta="right">Median R²</Table.Th>
              <Table.Th ta="right">% significant</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {sectors.map((s) => (
              <Table.Tr key={s.sector}>
                <Table.Td>{s.sector}</Table.Td>
                <Table.Td ta="right">{s.n}</Table.Td>
                <Table.Td ta="right">{fmtSigned(s.medTheme)}</Table.Td>
                <Table.Td ta="right">{fmtSigned(s.medInfra)}</Table.Td>
                <Table.Td ta="right">{fmtSigned(s.medExp, 4)}</Table.Td>
                <Table.Td ta="right">{fmtNum(s.medR2)}</Table.Td>
                <Table.Td ta="right">{s.pctSig.toFixed(1)}%</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </div>
  );
}

function median(values: number[]): number {
  if (values.length === 0) return NaN;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}