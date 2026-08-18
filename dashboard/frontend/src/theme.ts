import { createTheme } from '@mantine/core';

// Mantine theme derived from the Streamlit app's color palette
// (dashboard/app.py constants):
//   C_THEME  = #22d3ee  electric cyan  — AI Theme
//   C_INFRA  = #f59e0b  amber          — AI Infrastructure
//   C_ACCENT = #a78bfa  violet         — generic accent
//   C_GREEN  = #34d399  emerald
//   C_RED    = #f87171  red
//   C_GRAY   = #64748b  slate
export const theme = createTheme({
  primaryColor: 'theme',
  primaryShade: { light: 6, dark: 4 },
  defaultRadius: 'md',
  fontFamily: "Inter, 'Segoe UI', system-ui, -apple-system, sans-serif",
  fontFamilyMonospace: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  cursorType: 'pointer',
  focusRing: 'auto',
  colors: {
    theme: [
      '#ecfeff',
      '#cffafe',
      '#a5f3fc',
      '#67e8f9',
      '#22d3ee',
      '#06b6d4',
      '#0891b2',
      '#0e7490',
      '#155e75',
      '#164e63',
    ],
    infra: [
      '#fffbeb',
      '#fef3c7',
      '#fde68a',
      '#fcd34d',
      '#fbbf24',
      '#f59e0b',
      '#d97706',
      '#b45309',
      '#92400e',
      '#78350f',
    ],
    accent: [
      '#f5f3ff',
      '#ede9fe',
      '#ddd6fe',
      '#c4b5fd',
      '#a78bfa',
      '#8b5cf6',
      '#7c3aed',
      '#6d28d9',
      '#5b21b6',
      '#4c1d95',
    ],
    success: [
      '#ecfdf5',
      '#d1fae5',
      '#a7f3d0',
      '#6ee7b7',
      '#34d399',
      '#10b981',
      '#059669',
      '#047857',
      '#065f46',
      '#064e3b',
    ],
    danger: [
      '#fef2f2',
      '#fee2e2',
      '#fecaca',
      '#fca5a5',
      '#f87171',
      '#ef4444',
      '#dc2626',
      '#b91c1c',
      '#991b1b',
      '#7f1d1d',
    ],
    slate: [
      '#f8fafc',
      '#f1f5f9',
      '#e2e8f0',
      '#cbd5e1',
      '#94a3b8',
      '#64748b',
      '#475569',
      '#334155',
      '#1e293b',
      '#0f172a',
    ],
  },
});