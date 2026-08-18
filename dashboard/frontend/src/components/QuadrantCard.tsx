import { Card, Text, useMantineColorScheme } from '@mantine/core';

interface QuadrantCardProps {
  title: string;
  count: number;
  examples: string;
  accent: string;
}

// Quadrant summary card mirroring the Streamlit app's .quad-card.
export default function QuadrantCard({ title, count, examples, accent }: QuadrantCardProps) {
  const dark = useMantineColorScheme().colorScheme !== 'light';
  return (
    <Card
      withBorder
      radius="md"
      style={{
        borderTop: `3px solid ${accent}`,
        minHeight: 120,
        background: dark ? 'rgba(15,23,42,0.4)' : 'rgba(241,245,249,0.6)',
      }}
    >
      <Text fw={700} size="sm" style={{ color: accent }}>
        {title}
      </Text>
      <Text fz="1.5rem" fw={700} mt={2}>
        {count} stocks
      </Text>
      <Text size="xs" c="dimmed" mt={4}>
        {examples}
      </Text>
    </Card>
  );
}