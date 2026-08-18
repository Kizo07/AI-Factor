import { Text } from '@mantine/core';

// Section header mirroring the Streamlit app's .sec-header.
export default function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <Text
      fz="1.15rem"
      fw={650}
      mt="lg"
      mb="xs"
      style={{ borderLeft: '3px solid #a78bfa', paddingLeft: 10 }}
    >
      {children}
    </Text>
  );
}