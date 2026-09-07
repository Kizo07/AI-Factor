import { useMemo } from 'react';
import type { ComponentType } from 'react';
import { useMantineColorScheme } from '@mantine/core';
import Plotly from 'plotly.js-dist-min';
import * as PlotlyFactory from 'react-plotly.js/factory';
import type { PlotParams } from 'react-plotly.js';
import { SECTOR_PALETTE } from '../types';

// react-plotly.js/factory is a CommonJS module with a `default` export. Vite
// pre-bundles it as `{ default: { default: fn } }`, so unwrap defensively to
// always end up with the factory function itself.
const factoryModule = PlotlyFactory as unknown as { default: unknown };
const createPlotlyComponent = (
  typeof factoryModule.default === 'function'
    ? factoryModule.default
    : (factoryModule.default as { default: unknown }).default
) as (plotly: unknown) => ComponentType<PlotParams>;

const Plot = createPlotlyComponent(Plotly);

interface PlotProps {
  data: Plotly.Data[];
  layout?: Partial<Plotly.Layout>;
  height?: number;
  config?: Partial<Plotly.Config>;
}

// One Plotly template used by every chart — Cyan Ledger chrome (transparent
// backgrounds, cyan-tinted grid from the --line tokens, horizontal legend).
export default function PlotChart({ data, layout, height = 480, config }: PlotProps) {
  const { colorScheme } = useMantineColorScheme();
  const dark = colorScheme === 'dark';

  const baseLayout = useMemo(
    () => ({
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {
        color: dark ? '#a1b4c4' : '#445e72',
        family: "'Inter', system-ui, sans-serif",
        size: 13,
      },
      colorway: SECTOR_PALETTE,
      xaxis: {
        gridcolor: dark ? 'rgba(86,183,229,0.12)' : 'rgba(17,93,133,0.12)',
        zerolinecolor: dark ? 'rgba(86,183,229,0.25)' : 'rgba(17,93,133,0.25)',
        linecolor: dark ? 'rgba(86,183,229,0.34)' : 'rgba(17,93,133,0.32)',
      },
      yaxis: {
        gridcolor: dark ? 'rgba(86,183,229,0.12)' : 'rgba(17,93,133,0.12)',
        zerolinecolor: dark ? 'rgba(86,183,229,0.25)' : 'rgba(17,93,133,0.25)',
        linecolor: dark ? 'rgba(86,183,229,0.34)' : 'rgba(17,93,133,0.32)',
      },
      legend: {
        bgcolor: 'rgba(0,0,0,0)',
        orientation: 'h' as const,
        yanchor: 'bottom' as const,
        y: 1.02,
      },
      margin: { l: 40, r: 20, t: 50, b: 40 },
      hovermode: 'closest' as const,
      height,
    }),
    [dark, height],
  );

  return (
    <Plot
      data={data}
      layout={{ ...baseLayout, ...layout }}
      config={{
        displaylogo: false,
        responsive: true,
        ...config,
      }}
      style={{ width: '100%', height: '100%' }}
      useResizeHandler
    />
  );
}