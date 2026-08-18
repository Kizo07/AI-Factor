# Plan: S&P 500 AI Exposure Dashboard

**Created:** 2026-07-31
**Goal:** An interactive dashboard showing the market-implied AI exposure of every
S&P 500 stock, estimated from the project's AI Theme and AI Infrastructure factors,
using the latest available data ("as of yesterday").

---

## 1. Concept

For each S&P 500 stock *i*, estimate the regression from the Part-1 spec:

```
r_i,t − rf_t = α_i + β_theme·F_AITheme_t + β_infra·F_AIInfra_t + γ′·Controls_t + ε_i,t
Controls = [MKT, SMB, HML, RMW, CMA, UMD]   (daily Fama-French, decimal)
```

- **Window:** trailing 252 trading days (≈1 year), minimum 200 valid observations.
- **Inference:** OLS with Newey-West (HAC, 5 lags) t-statistics.
- **Outputs per stock:** β_theme, β_infra, their t-stats, α (annualized), R²,
  factor vols over the window, and **vol-scaled exposures** E = β·σ(F) (spec §21).
- **As-of dates:** stock/ETF data is refreshed through the last trading day
  ("yesterday"); FF controls lag to their publication date (currently 2026-05-29).
  The regression uses the trailing 252 days of *common* data; the dashboard
  displays all as-of dates transparently.

## 2. Data work (new pipeline code)

### 2.1 Refresh existing data
- `python -m src.main fetch --returns --no-cache` → ETF returns through yesterday.
- `python -m src.main construct` → AI factors through yesterday.

### 2.2 New: `src/pipelines/fetch_sp500.py`
- `SP500ConstituentFetcher` — S&P 500 constituent list from Wikipedia
  (ticker, name, GICS sector, GICS sub-industry), cached to
  `data/raw/sp500/sp500_constituents.feather`. Dot-tickers (BRK.B) are converted
  to Yahoo format (BRK-B).
- `StockReturnsFetcher` — batch daily adjusted-close history for all
  constituents via `yf.download` (2 years of history), converted to daily simple
  returns, cached to `data/raw/sp500/sp500_returns.feather`
  (columns: date, ticker, return, adj_close). Failed tickers are logged and
  skipped.

### 2.3 New: `src/analysis/estimate_exposure.py`
- `ExposureEstimator` with:
  - `estimate_current(returns, factors, ff_daily, window=252)` → one row per
    stock: ticker, name, sector, betas, t-stats, alpha_ann, r2, n_obs,
    factor vols, vol-scaled exposures, combined exposure
    (E_theme + E_infra), percentile ranks, AI quadrant label.
  - `rolling_betas(ticker, window=252)` → rolling beta time series for one
    stock (for the detail view).
  - `estimate_current(..., controls="market")` → fallback model using
    SPY − rf as the only control, valid through yesterday (no FF lag).
- Output: `data/exposure/sp500_ai_exposure_latest.feather` (+ `.csv`) and
  `data/exposure/metadata.json` (as-of dates, window, model, coverage counts).

## 3. Dashboard: `dashboard/app.py` (Streamlit + Plotly)

Dark, clean, professional quant-research look (custom CSS, wide layout,
consistent Plotly template). Sidebar holds global filters; main area is tabbed.

**Global controls (sidebar):**
- Model selector: FF5+UMD (default) vs Market-only (through yesterday)
- **Regression period: date-range slider (start AND end of the OLS sample).
  Default = precomputed trailing-252d window (instant load); any custom period
  recomputes the full cross-section on the fly (cached per period+model)**
- Estimation window: 126 / 252 (default) / 504 days (deep-dive rolling chart only)
- Sector multi-select, min-R² slider, ticker search box
- As-of date captions (prices / factors / FF controls)

**Tabs / features:**
1. **Overview** — metric cards (stocks covered, median β_theme, median β_infra,
   % of stocks with significant AI exposure at |t|≥2); AI exposure map:
   scatter β_theme × β_infra, colored by sector, quadrant guides, hover detail;
   quadrant summary cards (AI Leaders / Theme Plays / Infra Plays / Low Exposure).
2. **Leaderboards** — top/bottom N by theme beta, infra beta, combined
   vol-scaled exposure; significance highlighting.
3. **Stock Deep Dive** — ticker select → rolling β_theme/β_infra chart,
   price chart vs AI Theme factor (normalized), regression stats table,
   percentile gauges, peers in same sector.
4. **Sector Analysis** — median betas by GICS sector (bar), sector × exposure
   table, sector composition of the AI Leaders quadrant.
5. **Distributions** — histograms of β_theme / β_infra / combined exposure with
   median and 90th-percentile markers.
6. **Factors** — AI factor cumulative performance, rolling 63d theme–infra
   correlation, factor stats (reuses project data).
7. **Data & Methodology** — full sortable/filterable table with CSV download;
   methodology write-up with formulas, as-of dates, known limitations
   (FF publication lag, current-AUM weights, market-implied ≠ fundamental).

**Verification:** `streamlit.testing.v1.AppTest` smoke test + manual launch
(`streamlit run dashboard/app.py --server.headless true`) checking for a clean
200 response and error-free logs.

## 4. File changes

```
DASHBOARD_PLAN.md                     (this file)
src/pipelines/fetch_sp500.py          (new)
src/analysis/__init__.py              (new)
src/analysis/estimate_exposure.py     (new)
dashboard/app.py                      (new)
tests/test_exposure.py                (new: synthetic-data test of estimator)
requirements.txt                      (+ streamlit, plotly)
data/raw/sp500/  data/exposure/       (generated)
README.md / SESSION_HANDOFF.md        (updated at the end)
```

## 5. Execution order

1. Refresh ETF returns + rebuild factors (through yesterday).
2. Build & run the S&P 500 pipeline (constituents + returns).
3. Build the exposure estimator + tests; run for window 252 (FF model) and
   market-only model; write outputs.
4. Build the Streamlit dashboard; verify with AppTest + headless launch.
5. Update README/handoff.

## 6. Risks / decisions

- **FF publication lag** → market-only fallback model available through yesterday.
- **yfinance batch failures** → per-ticker try/except, log and skip; report coverage.
- **500-stock regression speed** → one regression per stock (~500 OLS fits,
  a few seconds with numpy/statsmodels); rolling series computed on demand per
  selected stock only.
