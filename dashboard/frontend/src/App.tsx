import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActionIcon,
  AppShell,
  Burger,
  Divider,
  Group,
  MultiSelect,
  Radio,
  RangeSlider,
  SegmentedControl,
  Slider,
  Stack,
  Tabs,
  Text,
  TextInput,
  Title,
  useMantineColorScheme,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconMoon, IconSun } from '@tabler/icons-react';
import { api } from './api';
import type {
  ExposureRow,
  FactorRow,
  Meta,
  Model,
} from './types';
import { MODEL_LABELS } from './types';
import OverviewView from './views/OverviewView';
import LeaderboardsView from './views/LeaderboardsView';
import DeepDiveView from './views/DeepDiveView';
import SectorView from './views/SectorView';
import DistributionsView from './views/DistributionsView';
import FactorsView from './views/FactorsView';
import DataMethodologyView from './views/DataMethodologyView';

const WINDOW_OPTIONS = [126, 252, 504];

function computeDefaultPeriod(
  model: Model,
  meta: Meta,
  tradingDays: string[],
): [number, number] {
  const modelEnd = model === 'ff' ? meta.ff_data_through : meta.price_data_through;
  const daysUptoEnd = tradingDays.filter((d) => d <= modelEnd);
  if (daysUptoEnd.length === 0) return [0, 0];
  const endIdx = daysUptoEnd.length - 1;
  const startIdx = Math.max(0, daysUptoEnd.length - meta.window);
  return [startIdx, endIdx];
}

export default function App() {
  const [mobileOpened, { toggle: toggleMobile }] = useDisclosure();
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();
  const [activeTab, setActiveTab] = useState<string | null>('overview');

  // --- static data -------------------------------------------------------
  const [meta, setMeta] = useState<Meta | null>(null);
  const [tradingDays, setTradingDays] = useState<string[]>([]);
  const [factors, setFactors] = useState<FactorRow[]>([]);

  // --- global filters ----------------------------------------------------
  const [model, setModel] = useState<Model>('ff');
  const [periodIdx, setPeriodIdx] = useState<[number, number]>([0, 0]);
  const [defaultPeriodIdx, setDefaultPeriodIdx] = useState<[number, number]>([0, 0]);
  const [windowLen, setWindowLen] = useState(252);
  const [sectors, setSectors] = useState<string[]>([]);
  const [allSectors, setAllSectors] = useState<string[]>([]);
  const [minR2, setMinR2] = useState(0);
  const [tickerQuery, setTickerQuery] = useState('');

  // --- cross-section -----------------------------------------------------
  const [exposure, setExposure] = useState<ExposureRow[]>([]);
  const [exposureLoading, setExposureLoading] = useState(true);
  const [recomputeLoading, setRecomputeLoading] = useState(false);
  const [periodSource, setPeriodSource] = useState('precomputed 252d window');
  const [error, setError] = useState<string | null>(null);
  const loadSeq = useRef(0);

  // --- initial load ------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    Promise.all([api.meta(), api.tradingDays(), api.factors()])
      .then(([m, td, fac]) => {
        if (cancelled) return;
        setMeta(m);
        setTradingDays(td.days);
        setFactors(fac.rows);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(String(e));
          setExposureLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // --- load exposure for a (model, period) ------------------------------
  const loadExposure = useCallback(
    async (m: Model, startDate: string, endDate: string, isDefault: boolean) => {
      const seq = ++loadSeq.current;
      setExposureLoading(true);
      setRecomputeLoading(!isDefault);
      setError(null);
      try {
        const res = isDefault
          ? await api.exposure(m)
          : await api.recompute(startDate, endDate, m);
        if (seq !== loadSeq.current) return;
        setExposure(res.rows);
        setPeriodSource(
          isDefault ? 'precomputed 252d window' : 'recomputed on the fly (cached)',
        );
      } catch (e) {
        if (seq !== loadSeq.current) return;
        setError(String(e));
        notifications.show({
          title: 'Failed to load exposure',
          message: String(e),
          color: 'red',
        });
      } finally {
        if (seq === loadSeq.current) {
          setExposureLoading(false);
          setRecomputeLoading(false);
        }
      }
    },
    [],
  );

  // --- when model changes: reset period to default and reload ------------
  useEffect(() => {
    if (!meta || tradingDays.length === 0) return;
    const [ds, de] = computeDefaultPeriod(model, meta, tradingDays);
    setDefaultPeriodIdx([ds, de]);
    setPeriodIdx([ds, de]);
    void loadExposure(model, tradingDays[ds], tradingDays[de], true);
  }, [model, meta, tradingDays, loadExposure]);

  // --- sector options from the loaded cross-section ----------------------
  useEffect(() => {
    const secs = [...new Set(exposure.map((r) => r.gics_sector).filter(Boolean))].sort() as string[];
    setAllSectors(secs);
    setSectors((prev) => (prev.length === 0 ? secs : prev.filter((s) => secs.includes(s))));
  }, [exposure]);

  // --- period slider commit ----------------------------------------------
  const handlePeriodChange = (val: [number, number]) => {
    setPeriodIdx(val);
    const [s, e] = val;
    const [ds, de] = defaultPeriodIdx;
    const isDefault = s === ds && e === de;
    void loadExposure(model, tradingDays[s], tradingDays[e], isDefault);
  };

  // --- derived filtered cross-section ------------------------------------
  const { valid, unestimable, medTheme, medInfra } = useMemo(() => {
    let rows = exposure;
    if (sectors.length > 0) {
      rows = rows.filter((r) => r.gics_sector !== null && sectors.includes(r.gics_sector));
    }
    rows = rows.filter((r) => (r.r2 ?? 0) >= minR2);
    const q = tickerQuery.trim().toUpperCase();
    if (q) {
      rows = rows.filter(
        (r) =>
          (r.ticker ?? '').toUpperCase().includes(q) ||
          (r.name ?? '').toUpperCase().includes(q),
      );
    }
    const validRows = rows.filter(
      (r) => r.beta_theme !== null && r.beta_infra !== null,
    );
    const unestimableRows = rows.filter((r) => r.beta_theme === null);
    const bt = validRows.map((r) => r.beta_theme as number);
    const bi = validRows.map((r) => r.beta_infra as number);
    return {
      valid: validRows,
      unestimable: unestimableRows,
      medTheme: median(bt),
      medInfra: median(bi),
    };
  }, [exposure, sectors, minR2, tickerQuery]);

  const periodCaption = useMemo(() => {
    if (tradingDays.length === 0) return '';
    const start = tradingDays[periodIdx[0]];
    const end = tradingDays[periodIdx[1]];
    const nCommon = tradingDays.filter((d) => d >= start && d <= end).length;
    const nEstimated = exposure.filter((r) => r.beta_theme !== null).length;
    return `Regression period: ${start} → ${end} (${nCommon} trading days, ${nEstimated} stocks estimated)`;
  }, [tradingDays, periodIdx, exposure]);

  const periodLabel = (v: number) => tradingDays[Math.round(v)] ?? '';

  return (
    <AppShell
      padding="md"
      header={{ height: 60 }}
      navbar={{
        width: 300,
        breakpoint: 'sm',
        collapsed: { mobile: !mobileOpened },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Burger
              opened={mobileOpened}
              onClick={toggleMobile}
              hiddenFrom="sm"
              size="sm"
            />
            <Title order={1} fz="1.4rem">📡 AI Exposure Terminal</Title>
            <Text size="xs" c="theme" tt="uppercase" fw={600} lts="0.08em" hiddenFrom="md">
              S&P 500 · Market-Implied AI Betas
            </Text>
          </Group>
          <ActionIcon
            variant="default"
            onClick={() => toggleColorScheme()}
            aria-label="Toggle color scheme"
          >
            {colorScheme === 'dark' ? <IconSun size={18} /> : <IconMoon size={18} />}
          </ActionIcon>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <AppShell.Section>
          <Text size="xs" c="theme" tt="uppercase" fw={600} lts="0.08em" mb="sm">
            S&P 500 · Market-Implied AI Betas
          </Text>
          <Divider mb="sm" />
        </AppShell.Section>

        <AppShell.Section grow component={Stack} gap="md">
          <Radio.Group
            value={model}
            onChange={(v) => setModel(v as Model)}
            label="Model"
          >
            <Stack gap={6} mt={4}>
              <Radio value="ff" label={MODEL_LABELS.ff} />
              <Radio value="market" label={MODEL_LABELS.market} />
            </Stack>
          </Radio.Group>

          <div role="group" aria-labelledby="period-label">
            <Text id="period-label" size="sm" fw={500} mb={4}>
              Regression period
            </Text>
            <RangeSlider
              value={periodIdx}
              onChange={setPeriodIdx}
              onChangeEnd={handlePeriodChange}
              min={0}
              max={Math.max(1, defaultPeriodIdx[1])}
              step={1}
              minRange={1}
              label={periodLabel}
              labelAlwaysOn
              thumbFromLabel="Period start"
              thumbToLabel="Period end"
              thumbValueText={(v) => periodLabel(v)}
              disabled={tradingDays.length === 0}
            />
            <Text size="xs" c="dimmed" mt={4}>
              {periodLabel(periodIdx[0])} → {periodLabel(periodIdx[1])}
            </Text>
          </div>

          <div>
            <Text size="sm" fw={500} mb={4}>
              Rolling window (deep-dive chart)
            </Text>
            <SegmentedControl
              aria-label="Rolling window"
              value={String(windowLen)}
              onChange={(v) => setWindowLen(Number(v))}
              data={WINDOW_OPTIONS.map((w) => ({ value: String(w), label: `${w}d` }))}
              fullWidth
            />
          </div>

          <MultiSelect
            label="GICS sectors"
            data={allSectors}
            value={sectors}
            onChange={setSectors}
            searchable
            clearable
            hidePickedOptions
            nothingFoundMessage="No sectors"
            maxDropdownHeight={220}
          />

          <div role="group" aria-labelledby="minr2-label">
            <Text id="minr2-label" size="sm" fw={500} mb={4}>
              Min R²
            </Text>
            <Slider
              aria-label="Min R²"
              value={minR2}
              onChange={setMinR2}
              min={0}
              max={1}
              step={0.05}
              label={(v) => v.toFixed(2)}
            />
          </div>

          <TextInput
            label="Ticker / name search"
            placeholder="e.g. NVDA"
            value={tickerQuery}
            onChange={(e) => setTickerQuery(e.currentTarget.value)}
          />
        </AppShell.Section>

        <AppShell.Section>
          <Divider my="sm" />
          <Text size="xs" c="dimmed">
            {periodCaption}
          </Text>
          <Text size="xs" c="dimmed">
            ({periodSource})
            {recomputeLoading && (
              <Text component="span" c="theme" fw={600}>
                {' '}
                — recomputing ~{meta?.n_stocks_total ?? '—'} regressions…
              </Text>
            )}
          </Text>
          {meta && (
            <>
              <Text size="xs" c="dimmed" mt={4}>
                Prices through: <b>{meta.price_data_through}</b>
              </Text>
              <Text size="xs" c="dimmed">
                AI factors through: <b>{meta.factor_data_through}</b>
              </Text>
              <Text size="xs" c="dimmed">
                FF controls through: <b>{meta.ff_data_through}</b>
              </Text>
            </>
          )}
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main>
        <Tabs value={activeTab} onChange={setActiveTab} keepMounted>
          <Tabs.List>
            <Tabs.Tab value="overview">Overview</Tabs.Tab>
            <Tabs.Tab value="leaderboards">Leaderboards</Tabs.Tab>
            <Tabs.Tab value="deepdive">Stock Deep Dive</Tabs.Tab>
            <Tabs.Tab value="sector">Sector Analysis</Tabs.Tab>
            <Tabs.Tab value="distributions">Distributions</Tabs.Tab>
            <Tabs.Tab value="factors">Factors</Tabs.Tab>
            <Tabs.Tab value="data">Data &amp; Methodology</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="overview" pt="md">
            <OverviewView
              valid={valid}
              unestimable={unestimable}
              medTheme={medTheme}
              medInfra={medInfra}
              meta={meta}
              model={model}
              periodCaption={periodCaption}
              exposureLoading={exposureLoading}
              error={error}
            />
          </Tabs.Panel>

          <Tabs.Panel value="leaderboards" pt="md">
            <LeaderboardsView valid={valid} exposureLoading={exposureLoading} error={error} />
          </Tabs.Panel>

          <Tabs.Panel value="deepdive" pt="md">
            <DeepDiveView
              exposure={exposure}
              factors={factors}
              model={model}
              windowLen={windowLen}
              periodCaption={periodCaption}
              exposureLoading={exposureLoading}
              error={error}
            />
          </Tabs.Panel>

          <Tabs.Panel value="sector" pt="md">
            <SectorView valid={valid} exposureLoading={exposureLoading} error={error} />
          </Tabs.Panel>

          <Tabs.Panel value="distributions" pt="md">
            <DistributionsView valid={valid} exposureLoading={exposureLoading} error={error} />
          </Tabs.Panel>

          <Tabs.Panel value="factors" pt="md">
            <FactorsView factors={factors} />
          </Tabs.Panel>

          <Tabs.Panel value="data" pt="md">
            <DataMethodologyView
              exposure={exposure}
              unestimable={unestimable}
              meta={meta}
              model={model}
              periodCaption={periodCaption}
              periodSource={periodSource}
              startDate={tradingDays[periodIdx[0]] ?? ''}
              endDate={tradingDays[periodIdx[1]] ?? ''}
              exposureLoading={exposureLoading}
              error={error}
            />
          </Tabs.Panel>
        </Tabs>
      </AppShell.Main>
    </AppShell>
  );
}

function median(values: number[]): number {
  if (values.length === 0) return NaN;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}