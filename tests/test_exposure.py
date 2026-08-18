"""Tests for the AI exposure estimator (synthetic data)."""

import numpy as np
import pandas as pd
import pytest

from src.analysis.estimate_exposure import estimate_current, rolling_betas


def _make_synthetic_data(
    n_days: int = 300,
    beta_theme: float = 1.5,
    beta_infra: float = 0.5,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate synthetic stock returns with known AI betas."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-01-01", periods=n_days)

    f_theme = rng.normal(0.0005, 0.01, n_days)
    f_infra = rng.normal(0.0004, 0.015, n_days)
    mkt_rf = rng.normal(0.0003, 0.01, n_days)
    rf = np.full(n_days, 0.0001)

    factors = pd.DataFrame(
        {
            "date": dates,
            "ai_theme_excess_return": f_theme,
            "ai_infra_excess_return": f_infra,
            "rf_rate": rf,
        }
    )
    ff_daily = pd.DataFrame(
        {
            "date": dates,
            "mkt_rf": mkt_rf,
            "smb": rng.normal(0, 0.005, n_days),
            "hml": rng.normal(0, 0.005, n_days),
            "rmw": rng.normal(0, 0.005, n_days),
            "cma": rng.normal(0, 0.005, n_days),
            "rf": rf,
            "umd": rng.normal(0, 0.005, n_days),
        }
    )

    # Stock with known betas on the AI factors and the market
    noise = rng.normal(0, 0.008, n_days)
    stock_ret = (
        rf
        + beta_theme * f_theme
        + beta_infra * f_infra
        + 1.0 * mkt_rf
        + noise
    )
    stock_returns = pd.DataFrame(
        {
            "date": dates,
            "ticker": "TEST",
            "adj_close": 100 * np.cumprod(1 + stock_ret),
            "return": stock_ret,
        }
    )
    # SPY rows so the 'market' control model can be built
    spy_returns = pd.DataFrame(
        {
            "date": dates,
            "ticker": "SPY",
            "adj_close": 100 * np.cumprod(1 + mkt_rf + rf),
            "return": mkt_rf + rf,
        }
    )

    constituents = pd.DataFrame(
        {
            "ticker": ["TEST"],
            "name": ["Test Corp"],
            "gics_sector": ["Information Technology"],
            "gics_sub_industry": ["Testing"],
        }
    )
    return stock_returns, spy_returns, factors, ff_daily, constituents


class TestEstimateCurrent:
    """Tests for estimate_current on synthetic data."""

    def test_recovers_known_betas_ff(self):
        """FF model recovers betas within tolerance."""
        stock_returns, _, factors, ff_daily, constituents = _make_synthetic_data()
        result = estimate_current(
            stock_returns, factors, ff_daily, constituents, window=252, min_obs=200
        )

        row = result.iloc[0]
        assert row["ticker"] == "TEST"
        assert row["n_obs"] == 252
        assert row["beta_theme"] == pytest.approx(1.5, abs=0.15)
        assert row["beta_infra"] == pytest.approx(0.5, abs=0.15)
        assert row["r2"] > 0.5
        assert row["exp_combined"] == pytest.approx(
            row["exp_theme"] + row["exp_infra"]
        )
        assert row["quadrant"] in (
            "AI Leader",
            "Theme Play",
            "Infra Play",
            "Low Exposure",
        )
        assert 0 <= row["pct_beta_theme"] <= 100

    def test_recovers_known_betas_market(self):
        """Market model recovers betas within tolerance."""
        stock_returns, spy_returns, factors, ff_daily, constituents = _make_synthetic_data()
        all_returns = pd.concat([stock_returns, spy_returns], ignore_index=True)
        result = estimate_current(
            all_returns,
            factors,
            ff_daily,
            constituents,
            window=252,
            min_obs=200,
            controls="market",
        )

        row = result.iloc[0]
        assert row["beta_theme"] == pytest.approx(1.5, abs=0.15)
        assert row["beta_infra"] == pytest.approx(0.5, abs=0.15)
        assert row["r2"] > 0.5

    def test_insufficient_observations_nan_betas(self):
        """Stocks with fewer than min_obs keep their row with NaN betas."""
        stock_returns, _, factors, ff_daily, constituents = _make_synthetic_data()
        # Keep only 100 days of stock data (< min_obs=200)
        short = stock_returns.tail(100).copy()
        result = estimate_current(
            short, factors, ff_daily, constituents, window=252, min_obs=200
        )

        row = result.iloc[0]
        assert row["ticker"] == "TEST"
        assert row["n_obs"] == 100
        assert np.isnan(row["beta_theme"])
        assert np.isnan(row["beta_infra"])
        assert np.isnan(row["r2"])
        assert row["quadrant"] is None


class TestCustomPeriod:
    """Tests for the start_date/end_date (custom period) path."""

    def test_date_range_recovers_betas(self):
        """Custom [start, end] period recovers betas within tolerance."""
        stock_returns, _, factors, ff_daily, constituents = _make_synthetic_data()
        dates = factors["date"]
        start, end = dates.iloc[50], dates.iloc[249]
        result = estimate_current(
            stock_returns, factors, ff_daily, constituents,
            start_date=str(start.date()), end_date=str(end.date()), min_obs=None,
        )

        row = result.iloc[0]
        assert row["n_obs"] == 200
        assert row["window_end"] == end
        assert row["beta_theme"] == pytest.approx(1.5, abs=0.15)
        assert row["beta_infra"] == pytest.approx(0.5, abs=0.15)
        assert row["r2"] > 0.5

    def test_short_period_adaptive_min_obs(self):
        """A 60-day period still estimates: the floor adapts to the period."""
        stock_returns, _, factors, ff_daily, constituents = _make_synthetic_data()
        dates = factors["date"]
        start, end = dates.iloc[60], dates.iloc[119]  # 60 trading days
        result = estimate_current(
            stock_returns, factors, ff_daily, constituents,
            start_date=str(start.date()), end_date=str(end.date()), min_obs=None,
        )

        row = result.iloc[0]
        assert row["n_obs"] == 60
        assert row["beta_theme"] == pytest.approx(1.5, abs=0.25)
        assert row["beta_infra"] == pytest.approx(0.5, abs=0.25)

    def test_fixed_min_obs_still_enforced(self):
        """An explicit min_obs is respected even in custom-period mode."""
        stock_returns, _, factors, ff_daily, constituents = _make_synthetic_data()
        dates = factors["date"]
        start, end = dates.iloc[60], dates.iloc[119]  # 60 days < min_obs=100
        result = estimate_current(
            stock_returns, factors, ff_daily, constituents,
            start_date=str(start.date()), end_date=str(end.date()), min_obs=100,
        )
        row = result.iloc[0]
        assert row["n_obs"] == 60
        assert np.isnan(row["beta_theme"])

    def test_stock_without_data_in_period_nan(self):
        """A stock with zero valid days in the period gets NaN betas, n_obs=0."""
        stock_returns, _, factors, ff_daily, constituents = _make_synthetic_data()
        dates = factors["date"]
        start, end = dates.iloc[200], dates.iloc[299]
        early_only = stock_returns[stock_returns["date"] < start].copy()
        result = estimate_current(
            early_only, factors, ff_daily, constituents,
            start_date=str(start.date()), end_date=str(end.date()), min_obs=None,
        )
        row = result.iloc[0]
        assert row["n_obs"] == 0
        assert np.isnan(row["beta_theme"])
        assert row["quadrant"] is None


class TestRollingBetas:
    """Tests for rolling_betas on synthetic data."""

    def test_rolling_betas_near_true_values(self):
        """Rolling betas average out near the true values."""
        stock_returns, _, factors, ff_daily, constituents = _make_synthetic_data()
        result = rolling_betas(
            stock_returns, factors, ff_daily, "TEST", window=252
        )

        assert list(result.columns) == ["date", "beta_theme", "beta_infra"]
        assert len(result) == 300 - 252 + 1
        assert result["beta_theme"].mean() == pytest.approx(1.5, abs=0.15)
        assert result["beta_infra"].mean() == pytest.approx(0.5, abs=0.15)
