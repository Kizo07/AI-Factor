"""AI Exposure Estimation for S&P 500 Stocks.

Per stock i, OLS with Newey-West (HAC, 5 lags) inference:

    r_i,t − rf_t = α + β_theme·F_theme + β_infra·F_infra + γ'·Controls + ε

Controls are either the daily Fama-French 5 factors + momentum ('ff') or
the market excess return only ('market', SPY − rf; valid through the latest
factor date, no FF publication lag).
"""

import json
import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm

from ..utils.config import get_config
from ..utils.storage import DataLoader, DataWriter

logger = logging.getLogger(__name__)

FF_CONTROL_COLS = ["mkt_rf", "smb", "hml", "rmw", "cma", "umd"]
MARKET_CONTROL_COLS = ["mkt_excess"]
FACTOR_COLS = ["f_theme", "f_infra"]

QUADRANT_LABELS = ("AI Leader", "Theme Play", "Infra Play", "Low Exposure")


def _build_factor_frame(
    factors: pd.DataFrame,
    ff_daily: pd.DataFrame,
    stock_returns: pd.DataFrame,
    controls: str,
) -> pd.DataFrame:
    """
    Build the regression right-hand-side frame.

    Args:
        factors: AI factor daily data (date, ai_theme_excess_return,
            ai_infra_excess_return, rf_rate, ...)
        ff_daily: Daily Fama-French factors in decimal
            (date, mkt_rf, smb, hml, rmw, cma, umd)
        stock_returns: Long-format stock returns (date, ticker, adj_close,
            return); used for the SPY market control
        controls: 'ff' (FF5 + UMD) or 'market' (SPY − rf)

    Returns:
        DataFrame with date, f_theme, f_infra, rf_rate and control columns,
        restricted to rows where everything needed is non-NaN.
    """
    frame = factors[["date", "ai_theme_excess_return", "ai_infra_excess_return", "rf_rate"]].copy()
    frame = frame.rename(
        columns={
            "ai_theme_excess_return": "f_theme",
            "ai_infra_excess_return": "f_infra",
        }
    )
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()

    if controls == "ff":
        ff = ff_daily[["date"] + FF_CONTROL_COLS].copy()
        ff["date"] = pd.to_datetime(ff["date"]).dt.normalize()
        frame = frame.merge(ff, on="date", how="left")
        required = FACTOR_COLS + ["rf_rate"] + FF_CONTROL_COLS
    elif controls == "market":
        spy = stock_returns[stock_returns["ticker"] == "SPY"][["date", "return"]].copy()
        if spy.empty:
            raise ValueError("SPY returns required for the 'market' control model")
        spy["date"] = pd.to_datetime(spy["date"]).dt.normalize()
        frame = frame.merge(spy.rename(columns={"return": "spy_return"}), on="date", how="left")
        frame["mkt_excess"] = frame["spy_return"] - frame["rf_rate"]
        frame = frame.drop(columns=["spy_return"])
        required = FACTOR_COLS + ["rf_rate"] + MARKET_CONTROL_COLS
    else:
        raise ValueError(f"Unknown controls: {controls!r} (expected 'ff' or 'market')")

    frame = frame.dropna(subset=required).sort_values("date").reset_index(drop=True)
    return frame


def _control_cols(controls: str) -> list[str]:
    """Return the control column names for a model variant."""
    if controls == "ff":
        return FF_CONTROL_COLS
    if controls == "market":
        return MARKET_CONTROL_COLS
    raise ValueError(f"Unknown controls: {controls!r} (expected 'ff' or 'market')")


def estimate_current(
    stock_returns: pd.DataFrame,
    factors: pd.DataFrame,
    ff_daily: pd.DataFrame,
    constituents: pd.DataFrame,
    window: int = 252,
    min_obs: Optional[int] = 200,
    controls: str = "ff",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Estimate current AI exposure for every stock in `constituents`.

    Args:
        stock_returns: Long-format returns (date, ticker, adj_close, return)
        factors: AI factor daily data
        ff_daily: Daily Fama-French factors (decimal)
        constituents: DataFrame with ticker, name, gics_sector
        window: Trailing window in trading days. Ignored when start_date or
            end_date is given.
        min_obs: Minimum observations for an estimate (below: NaN betas).
            If None, chosen adaptively as
            ``min(200, max(40, int(0.75 * n_available_days)))`` where
            n_available_days is the number of common factor dates in the
            selected sample — so short custom periods don't make every
            stock unestimable while still demanding ~3/4 coverage.
        controls: 'ff' (FF5 + UMD) or 'market' (SPY − rf)
        start_date: Optional first day (inclusive) of the regression sample.
        end_date: Optional last day (inclusive) of the regression sample.
            When either is given, each stock's sample is every trading day
            within [start_date, end_date] where all inputs are non-NaN,
            instead of the trailing `window` days.

    Returns:
        One row per stock: ticker, name, gics_sector, beta_theme, t_theme,
        beta_infra, t_infra, alpha_ann, r2, n_obs, window_end, vol_theme,
        vol_infra, exp_theme, exp_infra, exp_combined, percentile ranks
        (pct_beta_theme, pct_beta_infra, pct_exp_combined) and quadrant.
    """
    factor_frame = _build_factor_frame(factors, ff_daily, stock_returns, controls)
    control_cols = _control_cols(controls)
    regressors = FACTOR_COLS + control_cols

    custom_period = start_date is not None or end_date is not None
    start_ts = pd.Timestamp(start_date) if start_date is not None else None
    end_ts = pd.Timestamp(end_date) if end_date is not None else None

    if min_obs is None:
        # Adaptive floor: ~75% of the common factor days in the sample,
        # clamped to [40, 200].
        frame_dates = factor_frame["date"]
        if start_ts is not None:
            frame_dates = frame_dates[frame_dates >= start_ts]
        if end_ts is not None:
            frame_dates = frame_dates[frame_dates <= end_ts]
        if not custom_period:
            frame_dates = frame_dates.tail(window)
        n_available = len(frame_dates)
        min_obs = min(200, max(40, int(0.75 * n_available)))
        logger.info(f"Adaptive min_obs={min_obs} (n_available={n_available})")

    returns = stock_returns[["date", "ticker", "return"]].copy()
    returns["date"] = pd.to_datetime(returns["date"]).dt.normalize()

    rows = []
    for _, const in constituents.iterrows():
        ticker = const["ticker"]
        stock = returns[returns["ticker"] == ticker][["date", "return"]]
        merged = stock.merge(factor_frame, on="date", how="inner")
        merged["excess"] = merged["return"] - merged["rf_rate"]
        merged = merged.dropna(subset=["excess"] + regressors)
        if custom_period:
            # Every valid day inside [start_date, end_date]
            if start_ts is not None:
                merged = merged[merged["date"] >= start_ts]
            if end_ts is not None:
                merged = merged[merged["date"] <= end_ts]
            window_df = merged
        else:
            window_df = merged.tail(window)
        n_obs = len(window_df)

        row = {
            "ticker": ticker,
            "name": const.get("name"),
            "gics_sector": const.get("gics_sector"),
            "beta_theme": np.nan,
            "t_theme": np.nan,
            "beta_infra": np.nan,
            "t_infra": np.nan,
            "alpha_ann": np.nan,
            "r2": np.nan,
            "n_obs": n_obs,
            "window_end": window_df["date"].max() if n_obs else pd.NaT,
            "vol_theme": np.nan,
            "vol_infra": np.nan,
            "exp_theme": np.nan,
            "exp_infra": np.nan,
            "exp_combined": np.nan,
        }

        if n_obs >= min_obs:
            y = window_df["excess"].to_numpy()
            x = sm.add_constant(window_df[regressors].to_numpy())
            try:
                fit = sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
                vol_theme = window_df["f_theme"].std()
                vol_infra = window_df["f_infra"].std()
                beta_theme = fit.params[1]
                beta_infra = fit.params[2]
                row.update(
                    {
                        "beta_theme": beta_theme,
                        "t_theme": fit.tvalues[1],
                        "beta_infra": beta_infra,
                        "t_infra": fit.tvalues[2],
                        "alpha_ann": fit.params[0] * 252,
                        "r2": fit.rsquared,
                        "vol_theme": vol_theme,
                        "vol_infra": vol_infra,
                        "exp_theme": beta_theme * vol_theme,
                        "exp_infra": beta_infra * vol_infra,
                        "exp_combined": beta_theme * vol_theme + beta_infra * vol_infra,
                    }
                )
            except Exception as e:
                logger.warning(f"Regression failed for {ticker}: {e}")

        rows.append(row)

    result = pd.DataFrame(rows)

    # Percentile ranks (0-100) across stocks with valid estimates
    estimated = result["beta_theme"].notna()
    for col, pct_col in [
        ("beta_theme", "pct_beta_theme"),
        ("beta_infra", "pct_beta_infra"),
        ("exp_combined", "pct_exp_combined"),
    ]:
        result[pct_col] = np.nan
        result.loc[estimated, pct_col] = result.loc[estimated, col].rank(pct=True) * 100

    # Quadrant labels from cross-sectional medians
    med_theme = result.loc[estimated, "beta_theme"].median()
    med_infra = result.loc[estimated, "beta_infra"].median()

    def _quadrant(row) -> Optional[str]:
        if pd.isna(row["beta_theme"]) or pd.isna(row["beta_infra"]):
            return None
        high_theme = row["beta_theme"] > med_theme
        high_infra = row["beta_infra"] > med_infra
        if high_theme and high_infra:
            return "AI Leader"
        if high_theme:
            return "Theme Play"
        if high_infra:
            return "Infra Play"
        return "Low Exposure"

    result["quadrant"] = result.apply(_quadrant, axis=1)

    logger.info(
        f"Estimated {int(estimated.sum())}/{len(result)} stocks "
        f"(controls={controls}, window={window}, min_obs={min_obs})"
    )
    return result


def rolling_betas(
    stock_returns: pd.DataFrame,
    factors: pd.DataFrame,
    ff_daily: pd.DataFrame,
    ticker: str,
    window: int = 252,
    controls: str = "ff",
) -> pd.DataFrame:
    """
    Rolling beta_theme / beta_infra time series for one stock.

    Args:
        stock_returns: Long-format returns (date, ticker, adj_close, return)
        factors: AI factor daily data
        ff_daily: Daily Fama-French factors (decimal)
        ticker: Stock ticker
        window: Rolling window in trading days
        controls: 'ff' (FF5 + UMD) or 'market' (SPY − rf)

    Returns:
        DataFrame with columns: date, beta_theme, beta_infra (one row per
        window end date where a full window is available)
    """
    factor_frame = _build_factor_frame(factors, ff_daily, stock_returns, controls)
    control_cols = _control_cols(controls)
    regressors = FACTOR_COLS + control_cols

    stock = stock_returns[stock_returns["ticker"] == ticker][["date", "return"]].copy()
    stock["date"] = pd.to_datetime(stock["date"]).dt.normalize()

    merged = stock.merge(factor_frame, on="date", how="inner")
    merged["excess"] = merged["return"] - merged["rf_rate"]
    merged = merged.dropna(subset=["excess"] + regressors).sort_values("date").reset_index(drop=True)

    if len(merged) < window:
        logger.warning(f"Only {len(merged)} observations for {ticker}, window={window}")
        return pd.DataFrame(columns=["date", "beta_theme", "beta_infra"])

    y = merged["excess"].to_numpy()
    x = np.column_stack([np.ones(len(merged)), merged[regressors].to_numpy()])

    dates = []
    beta_themes = []
    beta_infras = []
    for end in range(window, len(merged) + 1):
        xw = x[end - window : end]
        yw = y[end - window : end]
        beta, _, _, _ = np.linalg.lstsq(xw, yw, rcond=None)
        dates.append(merged["date"].iloc[end - 1])
        beta_themes.append(beta[1])
        beta_infras.append(beta[2])

    return pd.DataFrame(
        {"date": dates, "beta_theme": beta_themes, "beta_infra": beta_infras}
    )


def main():
    """CLI entry point: run both models and write exposure outputs."""
    import argparse

    parser = argparse.ArgumentParser(description="Estimate S&P 500 AI exposure")
    parser.add_argument("--window", type=int, default=252, help="Estimation window")
    parser.add_argument("--min-obs", type=int, default=200, help="Minimum observations")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    config = get_config()
    loader_raw = DataLoader(config.raw_data_dir)
    writer = DataWriter(config.data_dir / "exposure")

    constituents = loader_raw.load_feather("sp500_constituents.feather", subfolder="sp500")
    stock_returns = loader_raw.load_feather("sp500_returns.feather", subfolder="sp500")
    factors = pd.read_feather(config.factors_dir / "ai_factor_daily.feather")
    ff_daily = pd.read_feather(config.reference_dir / "ff_factors_daily.feather")

    # SPY is an ETF, not an S&P 500 constituent; fetch it for the market control
    failed_tickers: list[str] = []
    if "SPY" not in set(stock_returns["ticker"].unique()):
        logger.info("SPY not in stock returns, fetching separately")
        from ..pipelines.fetch_sp500 import StockReturnsFetcher

        spy_fetcher = StockReturnsFetcher(config)
        spy = spy_fetcher.fetch(
            tickers=["SPY"], years=2, use_cache=False, filename="spy_returns.feather"
        )
        if spy.empty:
            logger.error("Failed to fetch SPY; market model unavailable")
            failed_tickers.append("SPY")
        else:
            stock_returns = pd.concat([stock_returns, spy], ignore_index=True)

    results = {}
    for controls in ["ff", "market"]:
        try:
            results[controls] = estimate_current(
                stock_returns,
                factors,
                ff_daily,
                constituents,
                window=args.window,
                min_obs=args.min_obs,
                controls=controls,
            )
        except Exception as e:
            logger.error(f"Model '{controls}' failed: {e}")

    if "ff" in results:
        writer.write_feather(results["ff"], "sp500_ai_exposure_latest.feather")
        writer.write_csv(results["ff"], "sp500_ai_exposure_latest.csv")
    if "market" in results:
        writer.write_feather(results["market"], "sp500_ai_exposure_market.feather")

    primary = results["ff"] if "ff" in results else results.get("market")
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "price_data_through": str(stock_returns["date"].max().date()),
        "factor_data_through": str(pd.to_datetime(factors["date"]).max().date()),
        "ff_data_through": str(
            ff_daily.dropna(subset=FF_CONTROL_COLS)["date"].max().date()
        ),
        "window": args.window,
        "n_stocks_total": int(len(primary)) if primary is not None else 0,
        "n_stocks_estimated": int(primary["beta_theme"].notna().sum())
        if primary is not None
        else 0,
        "failed_tickers": sorted(failed_tickers),
    }
    metadata_path = config.data_dir / "exposure" / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Wrote exposure outputs and metadata to {config.data_dir / 'exposure'}")
    for controls, df in results.items():
        estimated = df["beta_theme"].notna().sum()
        print(f"\n[{controls}] estimated {estimated}/{len(df)} stocks")
        top = df.nlargest(10, "exp_combined")[
            ["ticker", "name", "beta_theme", "beta_infra", "exp_combined", "quadrant"]
        ]
        print(top.to_string(index=False))


if __name__ == "__main__":
    main()
