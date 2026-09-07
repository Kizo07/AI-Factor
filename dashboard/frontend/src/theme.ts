import { createTheme } from '@mantine/core';

// "Cyan Ledger" theme ported from Kizo07.github.io (branch fusion/cyan-ledger):
// electric cyan × ledger gold, grotesk display headings, midnight / ice schemes.
// The per-scheme design tokens (--bg, --surface, --accent, --gold, ...) live in
// ./cyan-ledger.css; the palettes below keep Mantine's color scales on the same
// hues. The app's semantic color names are preserved and re-pointed at the
// Cyan Ledger ramps:
//   theme   → matrix cyan   (AI Theme factor, primary — the site's exact ramp)
//   infra   → ledger gold   (AI Infrastructure factor)
//   accent  → ledger green-teal (generic third series; was violet)
//   success → ledger green, danger/red → ledger red, slate → ledger blue-gray
export const theme = createTheme({
  primaryColor: 'theme',
  primaryShade: { dark: 5, light: 7 },
  defaultRadius: 'sm',
  cursorType: 'pointer',
  focusRing: 'auto',
  fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
  fontFamilyMonospace: "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace",
  headings: {
    fontFamily: "'Space Grotesk', 'Inter', system-ui, sans-serif",
    fontWeight: '500',
  },
  colors: {
    // Exact ramp from the source site's Mantine theme.
    theme: [
      '#e9faff',
      '#cef2ff',
      '#a0e8ff',
      '#6bdbff',
      '#36ceff',
      '#08bfff', // dark-scheme accent
      '#009ed9',
      '#007ea9', // light-scheme primary shade
      '#006484',
      '#004a63',
    ],
    // Ledger gold: shade 4 accents the dark scheme, shade 7 the light one.
    infra: [
      '#fdf3e3',
      '#f8e5c4',
      '#f1d59c',
      '#ecc374',
      '#e3ac55', // dark-scheme gold
      '#cf9440',
      '#b57d2e',
      '#8f621f', // light-scheme gold
      '#6f4b17',
      '#4f3510',
    ],
    // Ledger green-teal (#68dfcf on dark, #137665 on light).
    accent: [
      '#e6faf6',
      '#c2f2ea',
      '#96e6d8',
      '#68dfcf',
      '#45cdb8',
      '#30b8a1',
      '#209a86',
      '#137665',
      '#0f5a4d',
      '#0a3f36',
    ],
    success: [
      '#e6faf6',
      '#c2f2ea',
      '#96e6d8',
      '#68dfcf',
      '#45cdb8',
      '#30b8a1',
      '#209a86',
      '#137665',
      '#0f5a4d',
      '#0a3f36',
    ],
    // Ledger red (#f58ba4 on dark, #b0395d on light).
    danger: [
      '#fdeef2',
      '#f9dbe2',
      '#f3b8c6',
      '#ee8fa5',
      '#e66785',
      '#d6456b',
      '#c13a5e',
      '#b0395d',
      '#8a2c49',
      '#642037',
    ],
    red: [
      '#fdeef2',
      '#f9dbe2',
      '#f3b8c6',
      '#ee8fa5',
      '#e66785',
      '#d6456b',
      '#c13a5e',
      '#b0395d',
      '#8a2c49',
      '#642037',
    ],
    // Ledger blue-gray neutral ramp.
    slate: [
      '#f5faff',
      '#ecf4fa',
      '#e5f0f8',
      '#d3e3ee',
      '#b7cddc',
      '#9ab6c7',
      '#819aaa',
      '#506d82',
      '#2b4152',
      '#102d42',
    ],
    // Dark-scheme surfaces/text: 0 = text, 2 = dimmed, 4 = border,
    // 5 = hover, 6 = paper, 7 = body background.
    dark: [
      '#edf7fc',
      '#c9dde9',
      '#a1b4c4',
      '#819aaa',
      '#1e4254',
      '#0b1c28',
      '#07131d',
      '#020609',
      '#050c12',
      '#010304',
    ],
    // Light-scheme grays tinted toward ice blue; 6 = dimmed (#445e72).
    gray: [
      '#f5faff',
      '#ecf4fa',
      '#e5f0f8',
      '#d3e3ee',
      '#b7cddc',
      '#9ab6c7',
      '#445e72',
      '#3a5266',
      '#2b4152',
      '#102d42',
    ],
  },
});
