import { Card, Text, useMantineColorScheme } from '@mantine/core';

interface KpiCardProps {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}

// Metric card mirroring the Streamlit app's .kpi-card (accent left border),
// recolored to Cyan Ledger surfaces; default accent is the site's ledger gold.
export default function KpiCard({ label, value, sub, accent = 'var(--gold)' }: KpiCardProps) {
  const dark = useMantineColorScheme().colorScheme !== 'light';
  return (
    <Card
      withBorder
      radius="md"
      style={{
        borderLeft: `3px solid ${accent}`,
        minHeight: 92,
        background: dark ? 'linear-gradient(180deg, rgba(11,28,40,0.45), rgba(7,19,29,0.45))' : 'linear-gradient(180deg, rgba(229,240,248,0.6), rgba(255,255,255,0.5))',
      }}
    >
      <Text size="xs" tt="uppercase" c="dimmed" fw={600} lts="0.06em" mb={4}>
        {label}
      </Text>
      <Text fz="1.7rem" fw={700} lh={1.1}>
        {value}
      </Text>
      {sub ? (
        <Text size="xs" c="dimmed" mt={4}>
          {sub}
        </Text>
      ) : null}
    </Card>
  );
}