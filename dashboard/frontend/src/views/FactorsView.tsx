import { useMemo, useState } from 'react';
import { SimpleGrid, Switch, Text } from '@mantine/core';
import PlotChart from '../components/PlotChart';
import KpiCard from '../components/KpiCard';
import SectionTitle from '../components/SectionTitle';
import { fmtPct, fmtSigned } from '../format';
import type { FactorRow } from '../types';
import { C_ACCENT, C_INFRA, C_THEME } from '../types';

interface FactorsViewProps {
  factors: FactorRow[];
}

export default function FactorsView({ factors }: FactorsViewProps) {
  const [fullHistory, setFullHistory] = useState(false);

  const view = useMemo(() => {
    if (factors.length === 0) return { rows: [] as FactorRow[], cut: 0 };
    const cut = fullHistory ? 0 : factors.length - 3 * 252; // ~3 years
    return { rows: factors.slice(Math.max(0, cut)), cut };
  }, [factors, fullHistory]);

  const cumulative = useMemo(() => {
    let theme = 1;
    let infra = 1;
    const dates: string[] = [];
    const themeG: number[] = [];
    const infraG: number[] = [];
    for (const r of view.rows) {
      if (r.ai_theme_excess_return === null || r.rf_rate === null) continue;
      theme *= 1 + r.ai_theme_excess_return + r.rf_rate;
      if (r.ai_infra_excess_return !== null) {
        infra *= 1 + r.ai_infra_excess_return + r.rf_rate;
      }
      dates.push(r.date);
      themeG.push(theme);
      infraG.push(infra);
    }
    return { dates, themeG, infraG };
  }, [view.rows]);

  const corr = useMemo(() => {
    const t: number[] = [];
    const i: number[] = [];
    const d: string[] = [];
    for (const r of factors) {
      if (r.ai_theme_excess_return === null || r.ai_infra_excess_return === null) continue;
      t.push(r.ai_theme_excess_return);
      i.push(r.ai_infra_excess_return);
      d.push(r.date);
    }
    // rolling 63-day correlation
    const dates: string[] = [];
    const corrs: number[] = [];
    for (let k = 62; k < t.length; k += 1) {
      const sliceT = t.slice(k - 62, k + 1);
      const sliceI = i.slice(k - 62, k + 1);
      const corrVal = pearson(sliceT, sliceI);
      if (!Number.isNaN(corrVal)) {
        dates.push(d[k]);
        corrs.push(corrVal);
      }
    }
    return { dates, corrs };
  }, [factors]);

  const stats = useMemo(() => {
    const t = factors.map((r) => r.ai_theme_excess_return).filter((v): v is number => v !== null);
    const i = factors.map((r) => r.ai_infra_excess_return).filter((v): v is number => v !== null);
    const ann = (r: number[]) => {
      const mean = r.reduce((a, b) => a + b, 0) / r.length;
      const variance = r.reduce((a, b) => a + (b - mean) ** 2, 0) / (r.length - 1);
      const sd = Math.sqrt(variance);
      const ret = mean * 252;
      const vol = sd * Math.sqrt(252);
      return { ret, vol, sharpe: vol ? ret / vol : NaN };
    };
    const a = ann(t);
    const b = ann(i);
    return [
      { label: 'AI Theme ann. return', value: fmtPct(a.ret), sub: 'excess over rf', color: C_THEME },
      { label: 'AI Theme ann. vol', value: fmtPct(a.vol, 1), sub: 'σ·√252', color: C_THEME },
      { label: 'AI Theme Sharpe', value: fmtSigned(a.sharpe), sub: 'ann. ret / ann. vol', color: C_THEME },
      { label: 'AI Infra ann. return', value: fmtPct(b.ret), sub: 'excess over rf', color: C_INFRA },
      { label: 'AI Infra ann. vol', value: fmtPct(b.vol, 1), sub: 'σ·√252', color: C_INFRA },
      { label: 'AI Infra Sharpe', value: fmtSigned(b.sharpe), sub: 'ann. ret / ann. vol', color: C_INFRA },
    ];
  }, [factors]);

  return (
    <div>
      <Text fz="1.5rem" fw={700}>
        AI Factors
      </Text>

      <Switch
        label="Full history (since 2010)"
        checked={fullHistory}
        onChange={(e) => setFullHistory(e.currentTarget.checked)}
        mt="sm"
      />

      <SectionTitle>Cumulative performance — growth of $1</SectionTitle>
      <PlotChart
        data={[
          {
            type: 'scatter',
            mode: 'lines',
            x: cumulative.dates,
            y: cumulative.themeG,
            name: 'AI Theme',
            line: { color: C_THEME, width: 2 },
            hovertemplate: '%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>',
          },
          {
            type: 'scatter',
            mode: 'lines',
            x: cumulative.dates,
            y: cumulative.infraG,
            name: 'AI Infrastructure',
            line: { color: C_INFRA, width: 2 },
            hovertemplate: '%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>',
          },
        ]}
        height={420}
        layout={{ yaxis: { title: { text: 'Growth of $1' } } }}
      />
      <Text size="xs" c="dimmed">
        Long–short factor excess returns with the risk-free rate added back.
      </Text>

      <SectionTitle>Rolling 63d theme–infra correlation</SectionTitle>
      <PlotChart
        data={[
          {
            type: 'scatter',
            mode: 'lines',
            x: corr.dates,
            y: corr.corrs,
            name: '63d corr',
            line: { color: C_ACCENT, width: 1.8 },
            fill: 'tozeroy',
            fillcolor: 'rgba(167,139,250,0.12)',
            hovertemplate: '%{x|%Y-%m-%d}<br>corr: %{y:.2f}<extra></extra>',
          },
        ]}
        height={320}
        layout={{ yaxis: { title: { text: 'Correlation' } } }}
      />

      <SectionTitle>Factor statistics (full history, annualized)</SectionTitle>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
        {stats.map((s) => (
          <KpiCard key={s.label} label={s.label} value={s.value} sub={s.sub} accent={s.color} />
        ))}
      </SimpleGrid>
    </div>
  );
}

function pearson(a: number[], b: number[]): number {
  const n = a.length;
  if (n === 0) return NaN;
  const ma = a.reduce((x, y) => x + y, 0) / n;
  const mb = b.reduce((x, y) => x + y, 0) / n;
  let num = 0;
  let da = 0;
  let db = 0;
  for (let k = 0; k < n; k += 1) {
    num += (a[k] - ma) * (b[k] - mb);
    da += (a[k] - ma) ** 2;
    db += (b[k] - mb) ** 2;
  }
  return num / Math.sqrt(da * db);
}