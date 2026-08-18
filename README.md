# AI Exposure Factor Suite (Part 1)

**Part 1: ETF-Based Market-Implied AI Factors**

Builds two point-in-time ETF-derived AI return factors for later firm-level AI exposure estimation.

## Factors

1. **AI Theme Factor** (`F_AITheme`) — AUM-weighted basket of AI-focused ETFs (excluding semiconductors)
2. **AI Infrastructure Factor** (`F_AIInfra`) — Semiconductor/AI infrastructure ETF factor

## Project Structure

```
AI-Factor/
├── data/
│   ├── raw/           # Fetched data as-is
│   ├── processed/     # Cleaned, merged data
│   ├── factors/       # Final factor outputs
│   ├── reference/     # Reference data (FF factors, rf rate, calendar)
│   └── diagnostics/   # QC and analysis
├── src/
│   ├── pipelines/     # Data fetching scripts
│   ├── utils/         # Utilities (storage, validation, config)
│   └── main.py       # Main entry point
├── config/
│   ├── etf_classifications.csv  # ETF eligibility & bucket assignments
│   └── data_sources.yaml        # API configuration
├── tests/             # Tests
└── requirements.txt   # Python dependencies
```

## Setup

```bash
# Create an isolated environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Set up API keys (optional but recommended)
cp .env.example .env
# Edit .env with your FRED API key
```

Note: pandas is pinned to 2.x (`pandas==2.3.3` recommended) for
pandas-datareader compatibility.

## Usage

```bash
# Fetch all data
.venv/bin/python -m src.main fetch --all

# Fetch reference data (FF factors monthly + daily, rf rate, calendar)
.venv/bin/python -m src.main reference --all

# Construct factors and run diagnostics
.venv/bin/python -m src.main construct

# Run the test suite
.venv/bin/python -m pytest tests/ -q
```

## Analysis Notebooks

The `notebooks/` directory contains fully executed, step-by-step documentation
of the factor suite (run top-to-bottom with the project `.venv`):

1. **`01_data_and_etf_universe.ipynb`** — project goal, ETF eligibility
   universe and bucket classification, data sources, raw ETF returns/AUM
   coverage and quality checks, reference data (rf rate, FF factors, calendar).
2. **`02_factor_construction.ipynb`** — step-by-step construction of both
   factors using the project's own pipeline code: daily risk-free rate
   preparation, lagged AUM weights, theme basket aggregation, the SOXX infra
   factor, output schema, and validation checks.
3. **`03_factor_analysis.ipynb`** — factor performance and drawdowns,
   distributions and rolling volatility, correlation structure vs
   Fama-French factors, CAPM / FF5+UMD regressions with Newey-West errors,
   pre/post-ChatGPT regime analysis, and the SOXX-vs-SMH robustness check.

## S&P 500 AI Exposure Dashboard

Firm-level AI exposure estimates (rolling 252-day regressions of each S&P 500
stock's excess returns on the two AI factors with FF5+UMD controls) plus an
interactive Streamlit dashboard. See `DASHBOARD_PLAN.md` for the design.

```bash
# Rebuild the exposure estimates (fetches S&P 500 constituents + returns)
.venv/bin/python -m src.pipelines.fetch_sp500
.venv/bin/python -m src.analysis.estimate_exposure

# Launch the dashboard
.venv/bin/streamlit run dashboard/app.py
```

Features: exposure map (β_theme × β_infra by sector), leaderboards, per-stock
deep dive with rolling betas, sector analysis, distributions, factor
performance, and full data export. A market-only control model (valid through
the latest price date) is available alongside the FF5+UMD model. The
**regression period is user-selectable** via a sidebar date-range slider: the
default trailing-252-day window loads precomputed estimates instantly, and any
custom period recomputes all ~500 regressions on the fly (≈3 s, cached).

## Data Sources

| Data | Source | Cost |
|------|--------|------|
| ETF Returns | Yahoo Finance | Free |
| ETF AUM | Yahoo Finance | Free |
| FF Factors | Ken French Data Library | Free |
| Risk-Free Rate | FRED | Free |
| Trading Calendar | pandas-market-calendars | Free |

## Documentation

See `part_1_ai_exposure_factor_suite_etf_factors.md` for the full specification.

---

**Status:** Phase 1 complete — pipelines tested, factors constructed, full analysis documented in `notebooks/`. See `SESSION_HANDOFF.md` for the latest session notes.
