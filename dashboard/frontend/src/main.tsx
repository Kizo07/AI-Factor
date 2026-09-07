import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
// Cyan Ledger tokens load after Mantine so the --mantine-color-* mappings win.
import './cyan-ledger.css';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { createRoot } from 'react-dom/client';
import App from './App';
import { theme } from './theme';

createRoot(document.getElementById('root')!).render(
  <MantineProvider theme={theme} defaultColorScheme="dark">
    <Notifications />
    <App />
  </MantineProvider>,
);