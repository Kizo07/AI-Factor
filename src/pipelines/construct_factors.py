"""Factor Construction Pipeline.

Constructs the two AI factors:
1. AI Theme Factor (F_AITheme) - AUM-weighted basket of AI Theme ETFs
2. AI Infrastructure Factor (F_AIInfra) - Semiconductor ETF excess return
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from ..utils.config import get_config
from ..utils.storage import DataWriter
from ..utils.validation import (
    ValidationResult,
    validate_aum_staleness,
    validate_weights,
    compute_diagnostics,
    compute_correlation_diagnostics,
)

logger = logging.getLogger(__name__)


class FactorConstructor:
    """Constructs AI Theme and AI Infrastructure factors."""

    def __init__(self, config=None):
        """Initialize constructor with configuration."""
        self.config = config or get_config()
        self.writer = DataWriter(self.config.factors_dir)
        self.diagnostics_writer = DataWriter(self.config.diagnostics_dir)

        # Load configurations
        self._load_semicond_etf_choice()
        self._load_etf_classifications()

    @staticmethod
    def _annual_rf_to_daily(rf_annual: pd.Series) -> pd.Series:
        """Convert an annualized risk-free rate (decimal) to a daily rate.

        TB3MS from FRED is an annualized bond-equivalent yield in decimal form
        (e.g., 0.036 = 3.6% p.a.). Daily ETF returns require a *daily* rate, so
        we divide by 252 trading days (simple convention, consistent with the
        sqrt(252) annualization used in the diagnostics).

        Without this conversion the factor construction subtracts ~3.6% per
        *day* from daily returns, which corrupts every excess return.
        """
        return rf_annual / 252.0

    def _load_semicond_etf_choice(self):
        """Load semiconductor ETF choice from config file."""
        config_path = self.config.config_dir / "semicond_etf_choice.txt"

        if config_path.exists():
            with open(config_path, "r") as f:
                for line in f:
                    if line.startswith("PRIMARY:"):
                        self.primary_semi_etf = line.split(":")[1].strip()
                    elif line.startswith("ALTERNATIVE:"):
                        self.alternative_semi_etf = line.split(":")[1].strip()
        else:
            logger.warning("Semiconductor ETF choice file not found, using default SOXX")
            self.primary_semi_etf = "SOXX"
            self.alternative_semi_etf = "SMH"

        logger.info(f"Using {self.primary_semi_etf} as primary semiconductor ETF")

    def _load_etf_classifications(self):
        """Load ETF classifications from config file."""
        classification_path = self.config.config_dir / "etf_classifications.csv"

        if classification_path.exists():
            self.classifications = pd.read_csv(classification_path)

            # Convert date columns
            date_cols = ["inception_date", "inclusion_start_date", "inclusion_end_date"]
            for col in date_cols:
                if col in self.classifications.columns:
                    self.classifications[col] = pd.to_datetime(self.classifications[col], errors="coerce")

            logger.info(f"Loaded {len(self.classifications)} ETF classifications")
        else:
            logger.error("ETF classification file not found")
            self.classifications = pd.DataFrame()

    def construct_ai_theme_factor(
        self,
        etf_returns: pd.DataFrame,
        etf_aum: pd.DataFrame,
        rf_rate: pd.DataFrame,
        trading_calendar: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Construct the AI Theme Factor.

        F_AITheme_t = sum(w_e,t-1 * (R_e,t - Rf_t))

        where w_e,t-1 = AUM_e,t-1 / sum(AUM_j,t-1) for all j in Theme_t-1

        Args:
            etf_returns: DataFrame with columns [date, ticker, return]
            etf_aum: DataFrame with columns [ticker, aum, as_of_date]
            rf_rate: DataFrame with columns [date, rf_rate]
            trading_calendar: Optional trading calendar for alignment

        Returns:
            DataFrame with AI Theme factor data
        """
        logger.info("Constructing AI Theme Factor")

        # Get theme ETFs
        theme_etfs = self.classifications[
            self.classifications["bucket"] == "theme"
        ]["ticker"].tolist()

        if not theme_etfs:
            logger.error("No theme ETFs found in classifications")
            return pd.DataFrame()

        logger.info(f"Using {len(theme_etfs)} theme ETFs: {theme_etfs}")

        # Filter returns to theme ETFs
        theme_returns = etf_returns[etf_returns["ticker"].isin(theme_etfs)].copy()

        # Ensure date format - handle timezone-aware dates and normalize to midnight
        theme_returns["date"] = pd.to_datetime(theme_returns["date"], utc=True).dt.tz_localize(None).dt.normalize()
        rf_rate["date"] = pd.to_datetime(rf_rate["date"], utc=True).dt.tz_localize(None).dt.normalize()

        # Create a complete date range for rf_rate forward-filling
        min_date = theme_returns["date"].min()
        max_date = theme_returns["date"].max()
        # Start the rf window ~45 days before the first return date so the
        # forward-fill has a valid monthly observation for the first partial
        # month (monthly TB3MS is anchored on the 1st; without the lookback,
        # dates before the 1st of the first month got NaN rf).
        date_range = pd.date_range(
            start=min_date - pd.Timedelta(days=45), end=max_date, freq="D"
        )

        # Create daily rf_rate by forward-filling monthly data, then convert the
        # annualized rate to a daily rate before computing excess returns.
        rf_rate_daily = pd.DataFrame({"date": date_range})
        rf_rate_daily = rf_rate_daily.merge(rf_rate[["date", "rf_rate"]], on="date", how="left")
        rf_rate_daily["rf_rate"] = rf_rate_daily["rf_rate"].ffill()  # Forward-fill monthly rates to daily
        rf_rate_daily["rf_rate"] = self._annual_rf_to_daily(rf_rate_daily["rf_rate"])

        # Merge with risk-free rate
        theme_returns = theme_returns.merge(rf_rate_daily[["date", "rf_rate"]], on="date", how="left")

        # Compute excess returns
        theme_returns["excess_return"] = theme_returns["return"] - theme_returns["rf_rate"]

        # Get AUM data (current AUM will be forward-filled)
        # For now, use most recent AUM for each ETF
        aum_dict = etf_aum.set_index("ticker")["aum"].to_dict()

        # Assign AUM to returns
        theme_returns["aum"] = theme_returns["ticker"].map(aum_dict)

        # Handle monthly rebalancing: assign month-end AUM to next month's trading days
        theme_returns["month"] = theme_returns["date"].dt.to_period("M")
        theme_returns["month_start"] = theme_returns["date"].dt.to_period("M").dt.to_timestamp()

        # For each ETF, use last month's AUM for this month's weights
        # Simplified: use latest AUM and assume it applies forward.
        # Sort first so the shift(1) lag follows the time order of each ETF.
        theme_returns = theme_returns.sort_values(["ticker", "date"])
        theme_returns["aum_lagged"] = theme_returns.groupby("ticker")["aum"].transform(
            lambda x: x.ffill().shift(1).fillna(x.iloc[0] if len(x) > 0 else np.nan)
        )

        # Compute daily weights (only for ETFs with valid AUM)
        valid_aum = theme_returns[theme_returns["aum_lagged"].notna()]

        if valid_aum.empty:
            logger.error("No valid AUM data found for theme ETFs")
            return pd.DataFrame()

        # Compute daily weights: w_e,t = AUM_e,t-1 / sum(AUM_j,t-1)
        valid_aum["weight"] = valid_aum.groupby("date")["aum_lagged"].transform(
            lambda x: x / x.sum()
        )

        # Validate weights
        weight_validation = validate_weights(
            valid_aum,
            weight_col="weight",
            group_col="date",
            max_weight=self.config.max_single_etf_weight,
        )

        if not weight_validation.passed:
            logger.warning(f"Weight validation: {weight_validation.message}")

        # Construct factor: sum(w_e,t-1 * excess_return_e,t)
        # include_groups=False avoids the DataFrameGroupBy.apply deprecation
        # warning (the grouping column "date" is re-added by reset_index).
        factor_daily = valid_aum.groupby("date").apply(
            lambda x: pd.Series({
                # min_count=1: if every active ETF has a missing return (e.g.
                # an inception day), the factor is NaN rather than a fake 0.0
                "ai_theme_excess_return": (x["weight"] * x["excess_return"]).sum(min_count=1),
                "ai_theme_basket_return": (x["weight"] * x["return"]).sum(min_count=1),
                "active_theme_etf_count": len(x),
                "largest_theme_etf_weight": x["weight"].max(),
                "theme_etf_hhi": (x["weight"] ** 2).sum(),
                "rf_rate": x["rf_rate"].iloc[0] if not x["rf_rate"].isna().all() else np.nan,
            }),
            include_groups=False,
        ).reset_index()

        # Add data quality flag
        factor_daily["data_quality_flag"] = "ok"

        logger.info(f"Constructed AI Theme Factor: {len(factor_daily)} days")
        return factor_daily

    def construct_ai_infra_factor(
        self,
        etf_returns: pd.DataFrame,
        rf_rate: pd.DataFrame,
        use_alternative: bool = False,
    ) -> pd.DataFrame:
        """
        Construct the AI Infrastructure Factor.

        F_AIInfra_t = R_SemiETF_t - Rf_t

        Args:
            etf_returns: DataFrame with columns [date, ticker, return]
            rf_rate: DataFrame with columns [date, rf_rate]
            use_alternative: If True, use alternative semiconductor ETF

        Returns:
            DataFrame with AI Infra factor data
        """
        semi_ticker = self.alternative_semi_etf if use_alternative else self.primary_semi_etf

        logger.info(f"Constructing AI Infra Factor using {semi_ticker}")

        # Filter to semiconductor ETF
        semi_returns = etf_returns[etf_returns["ticker"] == semi_ticker].copy()

        if semi_returns.empty:
            logger.error(f"No returns found for semiconductor ETF {semi_ticker}")
            return pd.DataFrame()

        # Ensure date format - handle timezone-aware dates and normalize to midnight
        semi_returns["date"] = pd.to_datetime(semi_returns["date"], utc=True).dt.tz_localize(None).dt.normalize()
        rf_rate["date"] = pd.to_datetime(rf_rate["date"], utc=True).dt.tz_localize(None).dt.normalize()

        # Create a complete date range for rf_rate forward-filling
        min_date = semi_returns["date"].min()
        max_date = semi_returns["date"].max()
        # Start the rf window ~45 days before the first return date so the
        # forward-fill has a valid monthly observation for the first partial
        # month (monthly TB3MS is anchored on the 1st; without the lookback,
        # dates before the 1st of the first month got NaN rf).
        date_range = pd.date_range(
            start=min_date - pd.Timedelta(days=45), end=max_date, freq="D"
        )

        # Create daily rf_rate by forward-filling monthly data, then convert the
        # annualized rate to a daily rate before computing excess returns.
        rf_rate_daily = pd.DataFrame({"date": date_range})
        rf_rate_daily = rf_rate_daily.merge(rf_rate[["date", "rf_rate"]], on="date", how="left")
        rf_rate_daily["rf_rate"] = rf_rate_daily["rf_rate"].ffill()  # Forward-fill monthly rates to daily
        rf_rate_daily["rf_rate"] = self._annual_rf_to_daily(rf_rate_daily["rf_rate"])

        # Merge with risk-free rate
        semi_returns = semi_returns.merge(rf_rate_daily[["date", "rf_rate"]], on="date", how="left")

        # Compute excess return
        semi_returns["ai_infra_excess_return"] = semi_returns["return"] - semi_returns["rf_rate"]
        semi_returns["ai_infra_etf_return"] = semi_returns["return"]

        # Select output columns
        factor_daily = semi_returns[[
            "date",
            "ai_infra_excess_return",
            "ai_infra_etf_return",
            "rf_rate",
        ]].copy()

        factor_daily["data_quality_flag"] = "ok"
        factor_daily["semi_etf_used"] = semi_ticker

        logger.info(f"Constructed AI Infra Factor: {len(factor_daily)} days")
        return factor_daily

    def construct_factors(
        self,
        etf_returns: Optional[pd.DataFrame] = None,
        etf_aum: Optional[pd.DataFrame] = None,
        rf_rate: Optional[pd.DataFrame] = None,
        trading_calendar: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Construct both AI factors and merge into final output.

        Args:
            etf_returns: ETF returns data (if None, loads from file)
            etf_aum: ETF AUM data (if None, loads from file)
            rf_rate: Risk-free rate data (if None, loads from file)
            trading_calendar: Trading calendar (optional)

        Returns:
            DataFrame with both factors
        """
        logger.info("Constructing AI factors...")

        # Load data if not provided
        if etf_returns is None:
            etf_returns_path = self.config.raw_data_dir / "etf_returns" / "etf_returns.feather"
            if etf_returns_path.exists():
                etf_returns = pd.read_feather(etf_returns_path)
                etf_returns["date"] = pd.to_datetime(etf_returns["date"], utc=True).dt.tz_localize(None).dt.normalize()
            else:
                logger.error("ETF returns file not found")
                return pd.DataFrame()

        if etf_aum is None:
            etf_aum_path = self.config.raw_data_dir / "etf_aum" / "etf_aum_current.feather"
            if etf_aum_path.exists():
                etf_aum = pd.read_feather(etf_aum_path)
            else:
                logger.error("ETF AUM file not found")
                return pd.DataFrame()

        if rf_rate is None:
            rf_rate_path = self.config.reference_dir / "rf_rate_TB3MS.feather"
            if rf_rate_path.exists():
                rf_rate = pd.read_feather(rf_rate_path)
                rf_rate["date"] = pd.to_datetime(rf_rate["date"], utc=True).dt.tz_localize(None).dt.normalize()
            else:
                logger.error("Risk-free rate file not found")
                return pd.DataFrame()

        # Construct both factors
        ai_theme = self.construct_ai_theme_factor(etf_returns, etf_aum, rf_rate, trading_calendar)
        ai_infra = self.construct_ai_infra_factor(etf_returns, rf_rate)

        if ai_theme.empty or ai_infra.empty:
            logger.error("Failed to construct one or both factors")
            return pd.DataFrame()

        # Merge factors. Bring the infra rf_rate along as well: the theme
        # factor starts in 2013, so before that only the infra construction
        # has a valid daily rf. Coalesce so the output has a complete series.
        factors = ai_theme.merge(
            ai_infra[["date", "ai_infra_excess_return", "ai_infra_etf_return", "rf_rate"]],
            on="date",
            how="outer",
            suffixes=("", "_infra"),
        )
        factors["rf_rate"] = factors["rf_rate"].fillna(factors["rf_rate_infra"])
        factors = factors.drop(columns=["rf_rate_infra"])

        # Sort by date
        factors = factors.sort_values("date")

        # Save output
        self.writer.write_feather(factors, "ai_factor_daily.feather")

        # Also save weights
        self._save_weights(etf_returns, etf_aum)

        logger.info(f"Saved {len(factors)} days of AI factors")
        return factors

    def _save_weights(self, etf_returns: pd.DataFrame, etf_aum: pd.DataFrame):
        """Save daily ETF weights for transparency."""
        # Get theme ETFs
        theme_etfs = self.classifications[
            self.classifications["bucket"] == "theme"
        ]["ticker"].tolist()

        # Filter and compute weights (similar to factor construction)
        theme_returns = etf_returns[etf_returns["ticker"].isin(theme_etfs)].copy()
        theme_returns["date"] = pd.to_datetime(theme_returns["date"], utc=True).dt.tz_localize(None).dt.normalize()

        aum_dict = etf_aum.set_index("ticker")["aum"].to_dict()
        theme_returns["aum"] = theme_returns["ticker"].map(aum_dict)

        valid_aum = theme_returns[theme_returns["aum"].notna()].copy()
        valid_aum = valid_aum.sort_values(["ticker", "date"])
        valid_aum["aum_lagged"] = valid_aum.groupby("ticker")["aum"].transform(
            lambda x: x.ffill().shift(1).fillna(x.iloc[0] if len(x) > 0 else np.nan)
        )

        valid_aum["weight"] = valid_aum.groupby("date")["aum_lagged"].transform(
            lambda x: x / x.sum()
        )

        # Prepare weights output
        weights = valid_aum[[
            "date",
            "ticker",
            "aum",
            "weight",
        ]].copy()
        weights["bucket"] = "theme"
        weights["active_flag"] = True

        # Save
        self.writer.write_feather(weights, "ai_theme_weights.feather")

    def compute_diagnostics(
        self,
        factors: pd.DataFrame,
        ff_factors: Optional[pd.DataFrame] = None,
    ) -> dict:
        """
        Compute factor diagnostics.

        Args:
            factors: AI factors DataFrame
            ff_factors: Fama-French factors (optional, for correlation analysis)

        Returns:
            Dictionary with diagnostic results
        """
        logger.info("Computing factor diagnostics...")

        diagnostics = {}

        # AI Theme Factor diagnostics
        if "ai_theme_excess_return" in factors.columns:
            theme_returns = factors["ai_theme_excess_return"].dropna()
            diagnostics["ai_theme"] = compute_diagnostics(theme_returns)

        # AI Infra Factor diagnostics
        if "ai_infra_excess_return" in factors.columns:
            infra_returns = factors["ai_infra_excess_return"].dropna()
            diagnostics["ai_infra"] = compute_diagnostics(infra_returns)

        # Correlation between AI factors
        if "ai_theme_excess_return" in factors.columns and "ai_infra_excess_return" in factors.columns:
            aligned = factors[[
                "ai_theme_excess_return",
                "ai_infra_excess_return",
            ]].dropna()

            if len(aligned) > 0:
                diagnostics["correlation_ai_theme_infra"] = aligned["ai_theme_excess_return"].corr(
                    aligned["ai_infra_excess_return"]
                )

        # Correlation with FF factors (if provided)
        if ff_factors is not None and not ff_factors.empty:
            ff_factors = ff_factors.copy()
            ff_factors["date"] = pd.to_datetime(
                ff_factors["date"], utc=True
            ).dt.tz_localize(None).dt.normalize()
            merged = factors.merge(ff_factors, on="date", how="inner")

            if "ai_theme_excess_return" in merged.columns:
                for col in ["mkt_rf", "smb", "hml", "rmw", "cma", "umd"]:
                    if col in merged.columns:
                        corr = merged["ai_theme_excess_return"].corr(merged[col])
                        diagnostics[f"correlation_ai_theme_{col}"] = corr

            if "ai_infra_excess_return" in merged.columns:
                for col in ["mkt_rf", "smb", "hml", "rmw", "cma", "umd"]:
                    if col in merged.columns:
                        corr = merged["ai_infra_excess_return"].corr(merged[col])
                        diagnostics[f"correlation_ai_infra_{col}"] = corr

        # Save diagnostics - flatten nested dicts
        flat_diagnostics = {}
        for key, value in diagnostics.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    flat_diagnostics[f"{key}_{subkey}"] = subvalue
            else:
                flat_diagnostics[key] = value

        diag_df = pd.DataFrame([flat_diagnostics]).T.reset_index()
        diag_df.columns = ["metric", "value"]
        diag_df["value"] = diag_df["value"].astype(float)
        self.diagnostics_writer.write_feather(diag_df, "factor_summary.feather")

        logger.info(f"Computed {len(diagnostics)} diagnostic metrics")
        return diagnostics


def main():
    """CLI entry point for factor construction."""
    import argparse

    parser = argparse.ArgumentParser(description="Construct AI factors")
    parser.add_argument("--no-diagnostics", action="store_true", help="Skip diagnostics")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    constructor = FactorConstructor()

    # Construct factors
    factors = constructor.construct_factors()

    if factors.empty:
        logger.error("Failed to construct factors")
        return

    print(f"\nConstructed {len(factors)} days of AI factors")
    print(f"Date range: {factors['date'].min()} to {factors['date'].max()}")

    # Compute diagnostics
    if not args.no_diagnostics:
        # Load FF factors if available — prefer daily over monthly
        ff_daily_path = constructor.config.reference_dir / "ff_factors_daily.feather"
        ff_monthly_path = constructor.config.reference_dir / "ff_factors.feather"
        if ff_daily_path.exists():
            ff_factors = pd.read_feather(ff_daily_path)
        elif ff_monthly_path.exists():
            ff_factors = pd.read_feather(ff_monthly_path)
        else:
            ff_factors = None

        diagnostics = constructor.compute_diagnostics(factors, ff_factors)

        print("\nDiagnostics:")
        for key, value in diagnostics.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
