"""FastAPI backend for the S&P 500 AI Exposure dashboard (Mantine frontend).

Serves the same offline data files and analysis functions as the legacy
Streamlit app (``dashboard/app.py``) over a small typed JSON API:

- precomputed exposure cross-sections (FF5+UMD and Market-only models)
- AI factor daily series, FF controls, stock returns, constituents
- on-the-fly cross-sectional recompute for a custom regression period
  (delegates to ``src.analysis.estimate_exposure.estimate_current``)
- rolling beta series for one stock (``rolling_betas``)

The legacy Streamlit app is untouched and remains the primary launch path;
this backend is only consumed by the new Mantine frontend.

Run (from the project root or anywhere):

    .venv/bin/uvicorn dashboard.backend.app:app --host 127.0.0.1 --port 8000

or with the project venv:

    /tmp/opencode/aif-venv/bin/uvicorn dashboard.backend.app:app --port 8000
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Project root (parent of dashboard/backend) so the app works regardless of
# the current working directory — same trick as the Streamlit app.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.estimate_exposure import estimate_current, rolling_betas  # noqa: E402

MODEL_FILES = {
    "ff": "sp500_ai_exposure_latest.feather",
    "market": "sp500_ai_exposure_market.feather",
}

app = FastAPI(
    title="S&P 500 AI Exposure API",
    description="Offline JSON API backing the Mantine AI Exposure dashboard.",
    version="1.0.0",
)

# Loopback-only CORS: the Vite dev server (localhost:5173) is the only client.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# JSON serialization helpers (numpy / pandas -> plain JSON)
# --------------------------------------------------------------------------

def _clean(value: Any) -> Any:
    """Convert numpy/pandas scalars and NaN/NaT to JSON-safe values."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, dt.datetime, dt.date)):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, np.ndarray):
        return [_clean(v) for v in value.tolist()]
    return value


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame -> list of JSON-safe dicts (NaN -> null)."""
    return [
        {col: _clean(row[col]) for col in df.columns}
        for _, row in df.iterrows()
    ]


# --------------------------------------------------------------------------
# Data loading (cached, offline — same files as the Streamlit app)
# --------------------------------------------------------------------------

@lru_cache(maxsize=8)
def load_exposure(model: str) -> pd.DataFrame:
    if model not in MODEL_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model!r}")
    return pd.read_feather(PROJECT_ROOT / "data" / "exposure" / MODEL_FILES[model])


@lru_cache(maxsize=1)
def load_metadata() -> dict:
    with open(PROJECT_ROOT / "data" / "exposure" / "metadata.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_factors() -> pd.DataFrame:
    df = pd.read_feather(PROJECT_ROOT / "data" / "factors" / "ai_factor_daily.feather")
    df["date"] = pd.to_datetime(df["date"])
    return df


@lru_cache(maxsize=1)
def load_ff() -> pd.DataFrame:
    df = pd.read_feather(PROJECT_ROOT / "data" / "reference" / "ff_factors_daily.feather")
    df["date"] = pd.to_datetime(df["date"])
    return df


@lru_cache(maxsize=1)
def load_stock_returns() -> pd.DataFrame:
    """S&P 500 returns plus SPY (needed for the market-control rolling model)."""
    sr = pd.read_feather(PROJECT_ROOT / "data" / "raw" / "sp500" / "sp500_returns.feather")
    spy_path = PROJECT_ROOT / "data" / "raw" / "sp500" / "spy_returns.feather"
    if spy_path.exists():
        spy = pd.read_feather(spy_path)
        sr = pd.concat([sr, spy], ignore_index=True)
    sr["date"] = pd.to_datetime(sr["date"])
    return sr


@lru_cache(maxsize=1)
def load_constituents() -> pd.DataFrame:
    return pd.read_feather(
        PROJECT_ROOT / "data" / "raw" / "sp500" / "sp500_constituents.feather"
    )


@lru_cache(maxsize=1)
def load_trading_days() -> list[str]:
    """Sorted unique trading days available in the stock-returns panel."""
    sr = pd.read_feather(PROJECT_ROOT / "data" / "raw" / "sp500" / "sp500_returns.feather")
    days = sorted(pd.to_datetime(sr["date"]).dt.date.unique())
    return [d.isoformat() for d in days]


# Cache for on-the-fly recomputes, keyed by (start, end, model).
_recompute_cache: dict[tuple[str, str, str], pd.DataFrame] = {}


def compute_exposure_period(start: str, end: str, model: str) -> pd.DataFrame:
    """Recompute the full cross-section for a custom [start, end] period.

    ~500 OLS + Newey-West fits; measured ≈2-3 s — kept on the statsmodels
    HAC path (no approximation) and cached per (start, end, model).
    min_obs=None lets the estimator adapt its floor to the period length.
    """
    key = (start, end, model)
    if key in _recompute_cache:
        return _recompute_cache[key]
    result = estimate_current(
        load_stock_returns(),  # includes SPY for the market control
        load_factors(),
        load_ff(),
        load_constituents(),
        controls=model,
        start_date=start,
        end_date=end,
        min_obs=None,
    )
    _recompute_cache[key] = result
    return result


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict:
    return load_metadata()


@app.get("/api/exposure")
def exposure(
    model: str = Query("ff", pattern="^(ff|market)$"),
) -> dict:
    """Precomputed exposure cross-section for a model (default 252d window)."""
    df = load_exposure(model)
    return {"model": model, "rows": records(df)}


@app.post("/api/exposure/recompute")
def recompute(payload: dict) -> dict:
    """Recompute the full cross-section for a custom regression period."""
    model = payload.get("model", "ff")
    if model not in MODEL_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model!r}")
    raw_start = payload.get("start_date")
    raw_end = payload.get("end_date")
    try:
        start_d = dt.date.fromisoformat(str(raw_start))
        end_d = dt.date.fromisoformat(str(raw_end))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="start_date and end_date must be ISO dates (YYYY-MM-DD)",
        )
    start = start_d.isoformat()
    end = end_d.isoformat()

    # Refuse degenerately short periods (< ~40 common trading days), mirroring
    # the Streamlit app's guard.
    days = load_trading_days()
    day_dates = []
    for d in days:
        try:
            day_dates.append(dt.date.fromisoformat(str(d)))
        except ValueError:
            continue
    n_common = sum(1 for d in day_dates if start_d <= d <= end_d)
    if n_common < 40:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Selected period {start} → {end} spans only {n_common} common "
                "trading days — too few for a meaningful cross-sectional "
                "regression (minimum 40)."
            ),
        )
    df = compute_exposure_period(start, end, model)
    return {"model": model, "start_date": start, "end_date": end, "rows": records(df)}


@app.get("/api/factors")
def factors() -> dict:
    """AI factor daily series (theme + infra excess returns, rf)."""
    df = load_factors()
    cols = ["date", "ai_theme_excess_return", "ai_infra_excess_return", "rf_rate"]
    return {"rows": records(df[cols])}


@app.get("/api/returns")
def returns(ticker: str = Query(..., min_length=1)) -> dict:
    """Daily returns for one ticker (date, return) — deep-dive price chart."""
    sr = load_stock_returns()
    sub = sr[sr["ticker"] == ticker.upper()][["date", "return"]].dropna()
    return {"ticker": ticker.upper(), "rows": records(sub)}


@app.get("/api/trading-days")
def trading_days() -> dict:
    return {"days": load_trading_days()}


@app.get("/api/rolling-betas")
def rolling_betas_endpoint(
    ticker: str = Query(..., min_length=1),
    window: int = Query(252, ge=60, le=1000),
    model: str = Query("ff", pattern="^(ff|market)$"),
) -> dict:
    """Rolling beta_theme / beta_infra series for one stock."""
    rb = rolling_betas(
        load_stock_returns(), load_factors(), load_ff(),
        ticker.upper(), window=window, controls=model,
    )
    return {"ticker": ticker.upper(), "window": window, "model": model, "rows": records(rb)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)