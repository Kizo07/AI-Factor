// Ambient declarations for untyped modules used by the dashboard.

declare module '*.css';

declare module 'plotly.js-dist-min' {
  import * as Plotly from 'plotly.js';
  export = Plotly;
}