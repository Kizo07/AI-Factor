# Session Handoff: AI Factor Suite

**Date:** 2026-07-31 (end of day)
**Project:** `/home/fire/Documents/AI-Factor`
**Status:** Part 1 complete (factors + notebooks). Phase 2 started (S&P 500
exposure estimation + interactive dashboard).

---

## 1. What this project is

Builds **market-implied AI exposure factors** from ETF returns and uses them to
estimate firm-level AI exposure betas:

1. **AI Theme Factor** (`F_AITheme`) — lagged-AUM-weighted basket of 7 AI-theme
   ETF excess returns (BOTZ, IRBO, ROBO, AIQ, THNQ, WTAI, ARKQ). Starts
   2013-10-23 (ROBO inception).
2. **AI Infrastructure Factor** (`F_AIInfra`) — SOXX semiconductor ETF excess
   return (SMH as robustness alternative). Starts 2010-01-05 (data window).

Methodology spec: `part_1_ai_exposure_factor_suite_etf_factors.md`.

Firm-level model (per stock *i*, trailing OLS + Newey-West HAC 5 lags):

```
r_i,t − rf_t = α + β_theme·F_AITheme_t + β_infra·F_AIInfra_t + γ'·[MKT, SMB, HML, RMW, CMA, UMD] + ε
```

Vol-scaled exposures: `E = β·σ(F)`. Quadrants: AI Leader / Theme Play /
Infra Play / Low Exposure (vs cross-sectional medians).

---

## 2. Environment

- **`.venv/`** in the project root (Python 3.13.9). The old `ai-factor` conda
  env no longer exists — always use `.venv/bin/python`.
- **pandas pinned to 2.3.3** — pandas-datareader breaks on pandas 3.x.
- Key packages: yfinance, pandas-datareader, pandas-market-calendars, pyarrow,
  statsmodels, matplotlib, jupyter/nbconvert, streamlit 1.60, plotly 6.9,
  playwright (installed for dashboard screenshot verification only).
- Full list in `requirements.txt`.

---

## 3. How to run

```bash
cd /home/fire/Documents/AI-Factor

# Data pipeline
.venv/bin/python -m src.main fetch --returns --no-cache   # refresh ETF returns
.venv/bin/python -m src.main reference --all              # FF (monthly+daily), rf, calendar
.venv/bin/python -m src.main construct                    # rebuild factors + diagnostics

# S&P 500 exposure estimation
.venv/bin/python -m src.pipelines.fetch_sp500             # constituents + 2y returns
.venv/bin/python -m src.analysis.estimate_exposure        # both models -> data/exposure/

# Tests (20 total)
.venv/bin/python -m pytest tests/ -q

# Dashboard -> http://localhost:8501
.venv/bin/streamlit run dashboard/app.py

# Notebooks (fully executed documentation; run from project root)
.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/0X_*.ipynb
```

---

## 4. Current data state (as of 2026-07-31)

| Dataset | File | Coverage |
|---|---|---|
| AI factors | `data/factors/ai_factor_daily.feather` | 2010-01-04 → **2026-07-30** |
| ETF returns (9 ETFs) | `data/raw/etf_returns/etf_returns.feather` | → 2026-07-30 |
| FF factors daily (decimal) | `data/reference/ff_factors_daily.feather` | → **2026-05-29** (publication lag) |
| FF factors monthly (percent, legacy) | `data/reference/ff_factors.feather` | → 2026-04 |
| Risk-free rate (TB3MS, annualized) | `data/reference/rf_rate_TB3MS.feather` | → 2026-05 |
| S&P 500 returns (503 tickers) | `data/raw/sp500/sp500_returns.feather` | 2024-07-22 → 2026-07-30 |
| Exposure estimates (FF model) | `data/exposure/sp500_ai_exposure_latest.feather` | window ends 2026-05-29 |
| Exposure estimates (Market-only) | `data/exposure/sp500_ai_exposure_market.feather` | window ends 2026-07-30 |
| Exposure metadata | `data/exposure/metadata.json` | as-of dates, coverage |

**Factor stats (through 2026-07-30):** AI Theme 3,210 obs, 14.1%/yr mean excess,
22.8% vol · AI Infra 4,167 obs, 25.0%/yr, 30.8% vol · corr(theme, infra) ≈ 0.86 ·
corr with MKT ≈ 0.90 / 0.83.

**Exposure results:** 500/503 estimable (FDXF, HONA, Q are recent spin-offs with
< 200 obs). Top combined exposures: MU, SNDK, STX, WDC, LRCX, SMCI, AMD, TER,
AMAT, KLAC (all semis/hardware). NVDA: β_theme 0.117 (t 0.46), β_infra 0.312
(t 3.71), 91st percentile. Median S&P 500 β_theme −0.102, β_infra −0.071 —
the AI trade is concentrated, not broad.

---

## 5. Components

### Pipelines (`src/pipelines/`)
- `fetch_etf_returns.py` — yfinance daily adjusted returns, cached.
- `fetch_etf_aum.py` — current AUM snapshot (no historical AUM — see limitations).
- `fetch_reference_data.py` — FF factors (monthly + **daily**, decimal), TB3MS
  rf, NYSE calendar. Has a **direct-download fallback parser**
  (`_fetch_ff_csv_direct`) for FF datasets pandas-datareader can't parse
  (e.g. `F-F_Momentum_Factor_daily`).
- `fetch_sp500.py` — S&P 500 constituents (Wikipedia, dot→dash tickers) +
  batched `yf.download` returns.
- `construct_factors.py` — both factors + weights + diagnostics.

### Analysis (`src/analysis/`)
- `estimate_exposure.py` — `estimate_current()` (trailing `window` OR explicit
  `start_date`/`end_date` period; `min_obs=None` → adaptive floor
  `min(200, max(40, 0.75 × available days))`), `rolling_betas()` for one stock.
  Two control sets: `ff` (FF5+UMD) and `market` (SPY − rf).

### Dashboard (`dashboard/app.py`, Streamlit)
Dark quant-terminal UI, 7 tabs: Overview (β_theme × β_infra exposure map +
quadrants), Leaderboards, Stock Deep Dive (rolling betas, price vs factor),
Sector Analysis, Distributions, Factors, Data & Methodology (CSV export).
Sidebar: model selector, **regression-period date-range slider** (default =
precomputed 252d window; custom periods recompute ~500 regressions in ≈3.3 s,
cached), deep-dive window, sector/R²/search filters. Theme:
`.streamlit/config.toml`.

### Notebooks (`notebooks/`, fully executed, offline)
1. `01_data_and_etf_universe.ipynb` — universe, sources, raw-data QC.
2. `02_factor_construction.ipynb` — step-by-step build using the pipeline's own
   classes + validation.
3. `03_factor_analysis.ipynb` — performance, correlations, FF5+UMD regressions,
   regimes, SOXX-vs-SMH robustness.

### Tests — 20/20 pass
`test_pipelines.py` (8), `test_exposure.py` (8: synthetic beta recovery, custom
periods, min_obs paths, rolling betas), `test_dashboard.py` (4 AppTest runs).

---

## 6. Bugs fixed (chronological)

**Factor pipeline (2026-07-31 AM):**
1. **Critical:** annualized TB3MS was subtracted from *daily* returns (mean
   "excess" −1.79%/day). Fixed: `rf/252` via `_annual_rf_to_daily`.
2. FF correlations computed on ~1 day/month (only monthly FF existed; nonsense
   corr 0.015). Fixed: daily FF factors (`ff_factors_daily.feather`).
3. pandas-datareader can't parse `F-F_Momentum_Factor_daily` → direct-download
   fallback parser.
4. rf forward-fill gap at sample start (monthly TB3MS anchored on the 1st) →
   rf window now starts 45 days early; output `rf_rate` has zero NaN.
5. Fake 0.0 theme return on ROBO's inception day → `sum(min_count=1)` → NaN.
6. Housekeeping: `pct_change(fill_method=None)`, `groupby.apply(include_groups=False)`,
   pydantic v2 migration (`ConfigDict`, dropped deprecated `validator`), dead
   code, sort before lagged-AUM shift.

**Dashboard (2026-07-31 PM):**
7. Streamlit 1.60 registers its own plotly theme as global default → charts
   rendered white. Fix: explicit figure-level `paper_bgcolor`/`plot_bgcolor`/
   `font` in `styled_fig` + `st.plotly_chart(..., theme=None)`.
8. Red default widgets → `.streamlit/config.toml` dark theme, cyan primary.
9. Clipped sector labels → `automargin` on sector charts.

**Gotchas worth remembering:**
- AppTest: widget objects are stale after `run()` — re-fetch them; and
  `"text" in element` checks the proto, not `.value`.
- Streamlit health endpoint is `/_stcore/health`.
- Screenshot verification: playwright with `executable_path='/usr/bin/chromium'`.
- `pkill -f` patterns can self-match the invoking shell.

---

## 7. Known limitations

1. **Current-AUM weights** — theme basket weights use today's AUM across all
   history (no point-in-time AUM). Biggest methodological gap; Phase 2 target.
2. **FF publication lag** (~2 months) — FF5+UMD model's regression window ends
   2026-05-29. Market-only model covers through the latest price date.
3. **Trading calendar** has no early-close flags and extends ~1 year into the
   future (grid artifact).
4. **3 spin-offs** (FDXF, HONA, Q) not estimable — insufficient history.
5. Market-implied ≠ fundamental AI exposure; betas reflect co-movement,
   including sentiment/flows. One-year windows are regime-sensitive.

---

## 8. Suggested next steps

1. **Point-in-time AUM** — historical AUM/flows for theme ETFs (fixes limitation 1).
2. **Russell 1000 universe** — extend exposure estimation beyond the S&P 500.
3. **Rolling beta panels** — persist full time series of betas per stock, not
   just the current window.
4. **Capped / equal-weight theme variants** (spec §8 robustness).
5. Scheduling for daily refresh (Prefect/cron); the manual refresh sequence is
   in section 3.
6. Delisted-thematic-ETF research for survivorship-bias-free historical universe.

---

## 9. Session history (compact log)

- **2026-06-20** — Initial pipelines (ETF returns/AUM, reference data, factor
  construction); CSV→Feather conversion; pandas pinned to 2.3.3.
- **2026-07-31 AM** — Critical rf bug + FF-daily fix; factors regenerated;
  3 analysis notebooks created and verified; `.venv` established.
- **2026-07-31 PM** — S&P 500 pipeline + exposure estimator (FF5+UMD and
  Market-only models); Streamlit dashboard built and browser-verified;
  theming bugs fixed.
- **2026-07-31 PM-2** — User-selectable regression period (date-range slider,
  on-the-fly recompute ≈3.3 s cached); thorough bug check (numerical
  cross-check exact vs independent regression; 12 AppTest scenarios; 20/20 tests).

Key docs: `README.md` · `DASHBOARD_PLAN.md` ·
`part_1_ai_exposure_factor_suite_etf_factors.md` (methodology spec) ·
this file.
