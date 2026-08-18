"""Reference Data Fetching Pipeline.

Fetches:
1. Fama-French factors (from Ken French Data Library)
2. Risk-free rate (from FRED)
3. US Trading calendar (generated using pandas_market_calendars)
"""

import logging
import re
import zipfile
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from typing import Optional

import pandas as pd
import pandas_datareader.data as web
import pandas_market_calendars as mcal
import requests
from pandas.tseries.offsets import BDay

from ..utils.config import get_config
from ..utils.storage import DataWriter, get_cache_key, load_cache, save_cache

logger = logging.getLogger(__name__)


class ReferenceDataFetcher:
    """Fetches reference data for factor construction."""

    def __init__(self, config=None):
        """Initialize fetcher with configuration."""
        self.config = config or get_config()
        self.writer = DataWriter(self.config.reference_dir)
        self.cache_dir = self.config.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _fetch_ff_csv_direct(self, dataset: str, columns: list[str]) -> pd.DataFrame:
        """Download and parse a Ken French CSV zip directly.

        Fallback for datasets that pandas-datareader's famafrench parser cannot
        handle (e.g. F-F_Momentum_Factor_daily, whose file lacks the
        blank-line-separated table structure the parser expects).

        Args:
            dataset: Dataset name, e.g. 'F-F_Momentum_Factor_daily'
            columns: Column names for the parsed data, e.g. ['date', 'umd']

        Returns:
            DataFrame with a datetime 'date' column and float value columns.
        """
        base_url = self.config.data_sources.fama_french.base_url
        url = f"{base_url}/{dataset}_CSV.zip"

        logger.info(f"Downloading {url} directly")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with zipfile.ZipFile(BytesIO(response.content)) as z:
            raw = z.read(z.namelist()[0]).decode("utf-8", errors="replace")

        # Data rows start with an 8-digit date (daily) or 6-digit date (monthly)
        row_pattern = re.compile(r"^\s*(\d{8}|\d{6})\s*,")
        rows = [
            line for line in raw.splitlines()
            if row_pattern.match(line) and "-99" not in line  # drop missing-data flags
        ]

        parsed = pd.read_csv(
            StringIO("\n".join(rows)),
            header=None,
            usecols=list(range(len(columns))),
            names=columns,
        )
        date_fmt = "%Y%m%d" if len(str(parsed["date"].iloc[0])) == 8 else "%Y%m"
        parsed["date"] = pd.to_datetime(parsed["date"], format=date_fmt)

        return parsed

    @staticmethod
    def _is_valid_ff_frame(df: pd.DataFrame, expected_cols: int) -> bool:
        """Check that a parsed FF frame has the expected shape and no NaN columns."""
        return not df.empty and len(df.columns) == expected_cols

    def fetch_fama_french_factors(
        self,
        dataset: str = "F-F_Research_Data_5_Factors_2x3",
        use_cache: bool = True,
        daily: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch Fama-French factors from Ken French Data Library.

        Args:
            dataset: Dataset name
                - 'F-F_Research_Data_5_Factors_2x3': 5-factor (MKT, SMB, HML, RMW, CMA)
                - 'F-F_Momentum_Factor': Momentum (UMD)
            use_cache: Whether to use cached data
            daily: If True, fetch the daily variant of the dataset and convert
                values from percent to decimal. If False (default), fetch the
                monthly variant (kept in percent, as published).

        Returns:
            DataFrame with columns: date, mkt_rf, smb, hml, rmw, cma, rf
        """
        if daily:
            dataset = f"{dataset}_daily"

        cache_key = get_cache_key({"dataset": dataset, "function": "fetch_ff_factors"})

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info(f"Loaded cached Fama-French data: {dataset}")
                return cached

        try:
            logger.info(f"Fetching Fama-French dataset: {dataset}")

            # Fetch from pandas_datareader (wraps Ken French library)
            ff_data = web.DataReader(dataset, "famafrench", start="1900-01-01")[0]

            # Reset index to get date as column
            ff_data = ff_data.reset_index()
            ff_data.columns = ["date", "mkt_rf", "smb", "hml", "rmw", "cma", "rf"]

            # Convert date - monthly data comes back as a PeriodIndex
            if hasattr(ff_data["date"].iloc[0], "to_timestamp"):
                ff_data["date"] = ff_data["date"].dt.to_timestamp()
            else:
                ff_data["date"] = pd.to_datetime(ff_data["date"])

            if daily:
                # Daily factors are published in percent; convert to decimal so
                # they are directly comparable to the AI factor returns.
                factor_cols = ["mkt_rf", "smb", "hml", "rmw", "cma", "rf"]
                ff_data[factor_cols] = ff_data[factor_cols] / 100.0

            # Save to cache
            if use_cache and self.config.data_sources.cache.enabled:
                save_cache(ff_data, self.cache_dir, cache_key, suffix=".feather")

            # Save to reference directory
            suffix = "_daily" if daily else ""
            self.writer.write_feather(ff_data, f"ff_factors_5_factor{suffix}.feather")

            logger.info(f"Fetched {len(ff_data)} rows of Fama-French data ({dataset})")
            return ff_data

        except Exception as e:
            logger.error(f"Error fetching Fama-French data: {e}")
            return pd.DataFrame()

    def fetch_momentum_factor(
        self,
        use_cache: bool = True,
        daily: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch Fama-French Momentum factor.

        Args:
            use_cache: Whether to use cached data
            daily: If True, fetch the daily variant and convert percent to
                decimal. If False (default), fetch the monthly variant.

        Returns:
            DataFrame with columns: date, umd
        """
        dataset = "F-F_Momentum_Factor_daily" if daily else "F-F_Momentum_Factor"
        cache_key = get_cache_key({"function": "fetch_momentum_factor", "daily": daily})

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info("Loaded cached Momentum factor data")
                return cached

        try:
            logger.info(f"Fetching Fama-French Momentum factor ({dataset})")

            try:
                # Fetch momentum factor via pandas-datareader
                mom_data = web.DataReader(dataset, "famafrench", start="1900-01-01")[0]

                # Reset index
                mom_data = mom_data.reset_index()
                mom_data.columns = ["date", "umd"]
            except Exception as e:
                # pandas-datareader cannot parse some datasets (e.g. the daily
                # momentum file); fall back to direct download + manual parsing.
                logger.warning(f"pandas-datareader failed ({e}), using direct download")
                mom_data = self._fetch_ff_csv_direct(dataset, ["date", "umd"])

            # Convert date - monthly data comes back as a PeriodIndex
            if hasattr(mom_data["date"].iloc[0], "to_timestamp"):
                mom_data["date"] = mom_data["date"].dt.to_timestamp()
            else:
                mom_data["date"] = pd.to_datetime(mom_data["date"])

            if daily:
                mom_data["umd"] = mom_data["umd"] / 100.0

            # Save to cache
            if use_cache and self.config.data_sources.cache.enabled:
                save_cache(mom_data, self.cache_dir, cache_key, suffix=".feather")

            # Save to reference directory
            suffix = "_daily" if daily else ""
            self.writer.write_feather(mom_data, f"ff_factors_momentum{suffix}.feather")

            logger.info(f"Fetched {len(mom_data)} rows of Momentum data ({dataset})")
            return mom_data

        except Exception as e:
            logger.error(f"Error fetching Momentum factor: {e}")
            return pd.DataFrame()

    def merge_ff_factors(
        self,
        factors_5f: Optional[pd.DataFrame] = None,
        momentum: Optional[pd.DataFrame] = None,
        use_cache: bool = True,
        daily: bool = False,
    ) -> pd.DataFrame:
        """
        Merge all Fama-French factors into one DataFrame.

        Args:
            factors_5f: 5-factor data (if None, will fetch)
            momentum: Momentum data (if None, will fetch)
            use_cache: Whether to use cached data
            daily: If True, fetch/merge the daily factor variants (decimal).
                The merged daily file is what factor diagnostics should use,
                since the AI factors are daily series.

        Returns:
            DataFrame with all FF factors
        """
        cache_key = get_cache_key({"function": "merge_ff_factors", "daily": daily})

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info("Loaded cached merged FF factors")
                return cached

        # Fetch if not provided
        if factors_5f is None:
            factors_5f = self.fetch_fama_french_factors(use_cache=use_cache, daily=daily)

        if momentum is None:
            momentum = self.fetch_momentum_factor(use_cache=use_cache, daily=daily)

        # Merge
        if not factors_5f.empty and not momentum.empty:
            merged = factors_5f.merge(momentum, on="date", how="outer")

            # Save
            if use_cache and self.config.data_sources.cache.enabled:
                save_cache(merged, self.cache_dir, cache_key, suffix=".feather")

            suffix = "_daily" if daily else ""
            self.writer.write_feather(merged, f"ff_factors{suffix}.feather")

            logger.info(f"Merged {len(merged)} rows of FF factors (daily={daily})")
            return merged
        elif not factors_5f.empty:
            logger.warning("Momentum data not available, returning 5-factor only")
            return factors_5f
        else:
            logger.error("Failed to fetch any FF factor data")
            return pd.DataFrame()

    def fetch_risk_free_rate(
        self,
        series_id: str = "TB3MS",  # 3-month Treasury bill
        start_date: str = "1900-01-01",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch risk-free rate from FRED.

        Args:
            series_id: FRED series ID
                - 'TB3MS': 3-month T-bill (monthly)
                - 'DTB3': 3-month T-bill (daily)
            start_date: Start date
            use_cache: Whether to use cached data

        Returns:
            DataFrame with columns: date, rf_rate
        """
        cache_key = get_cache_key({"series_id": series_id, "function": "fetch_rf_rate"})

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info(f"Loaded cached risk-free rate: {series_id}")
                return cached

        try:
            logger.info(f"Fetching risk-free rate from FRED: {series_id}")

            # Fetch from FRED
            rf_data = web.DataReader(series_id, "fred", start=start_date)

            rf_data = rf_data.reset_index()
            rf_data.columns = ["date", "rf_rate"]

            # Convert to decimal (percent to decimal)
            rf_data["rf_rate"] = rf_data["rf_rate"] / 100

            # Save to cache
            if use_cache and self.config.data_sources.cache.enabled:
                save_cache(rf_data, self.cache_dir, cache_key, suffix=".feather")

            # Save to reference directory
            self.writer.write_feather(rf_data, f"rf_rate_{series_id}.feather")

            logger.info(f"Fetched {len(rf_data)} rows of risk-free rate data")
            return rf_data

        except Exception as e:
            logger.error(f"Error fetching risk-free rate: {e}")
            return pd.DataFrame()

    def generate_trading_calendar(
        self,
        start_date: str = "1900-01-01",
        end_date: Optional[str] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Generate US trading calendar (NYSE/NASDAQ).

        Args:
            start_date: Start date
            end_date: End date (defaults to 1 year from now)
            use_cache: Whether to use cached data

        Returns:
            DataFrame with columns: date, is_trading_day, is_early_close
        """
        if end_date is None:
            end_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

        cache_key = get_cache_key({
            "start_date": start_date,
            "end_date": end_date,
            "function": "generate_trading_calendar",
        })

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info("Loaded cached trading calendar")
                return cached

        try:
            logger.info(f"Generating trading calendar from {start_date} to {end_date}")

            # Create NYSE calendar
            nyse = mcal.get_calendar("XNYS")  # NYSE calendar

            # Get trading days - returns timezone-aware DatetimeIndex
            trading_days = nyse.valid_days(start_date=start_date, end_date=end_date)
            # Convert to timezone-naive dates for comparison
            trading_days = trading_days.tz_localize(None)

            # Create full date range
            all_dates = pd.date_range(start=start_date, end=end_date, freq="D")

            # Create calendar DataFrame
            calendar_df = pd.DataFrame({"date": all_dates})
            calendar_df["is_trading_day"] = calendar_df["date"].isin(trading_days)
            calendar_df["is_early_close"] = False  # Early closes would need separate handling

            # Save to cache
            if use_cache and self.config.data_sources.cache.enabled:
                save_cache(calendar_df, self.cache_dir, cache_key, suffix=".feather")

            # Save to reference directory
            self.writer.write_feather(calendar_df, "trading_calendar.feather")

            trading_day_count = calendar_df["is_trading_day"].sum()
            logger.info(f"Generated calendar with {trading_day_count} trading days")

            return calendar_df

        except Exception as e:
            logger.error(f"Error generating trading calendar: {e}")
            return pd.DataFrame()

    def fetch_all(
        self,
        start_date: str = "1900-01-01",
        use_cache: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch all reference data.

        Args:
            start_date: Start date for calendar and risk-free rate
            use_cache: Whether to use cached data

        Returns:
            Dictionary with DataFrames: ff_factors, rf_rate, trading_calendar
        """
        logger.info("Fetching all reference data...")

        results = {
            "ff_factors": self.merge_ff_factors(use_cache=use_cache),
            "ff_factors_daily": self.merge_ff_factors(use_cache=use_cache, daily=True),
            "rf_rate": self.fetch_risk_free_rate(start_date=start_date, use_cache=use_cache),
            "trading_calendar": self.generate_trading_calendar(start_date=start_date, use_cache=use_cache),
        }

        for name, df in results.items():
            if df.empty:
                logger.warning(f"Failed to fetch {name}")
            else:
                logger.info(f"Successfully fetched {name}: {len(df)} rows")

        return results


def main():
    """CLI entry point for reference data fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch reference data")
    parser.add_argument("--ff-factors", action="store_true", help="Fetch Fama-French factors")
    parser.add_argument("--rf-rate", action="store_true", help="Fetch risk-free rate")
    parser.add_argument("--calendar", action="store_true", help="Generate trading calendar")
    parser.add_argument("--all", action="store_true", help="Fetch all reference data")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    fetcher = ReferenceDataFetcher()

    if args.all or not any([args.ff_factors, args.rf_rate, args.calendar]):
        # Default: fetch all
        results = fetcher.fetch_all(use_cache=not args.no_cache)
        for name, df in results.items():
            if not df.empty:
                print(f"\n{name}: {len(df)} rows")
    else:
        if args.ff_factors:
            df = fetcher.merge_ff_factors(use_cache=not args.no_cache)
            print(f"Fama-French factors: {len(df)} rows")

        if args.rf_rate:
            df = fetcher.fetch_risk_free_rate(use_cache=not args.no_cache)
            print(f"Risk-free rate: {len(df)} rows")

        if args.calendar:
            df = fetcher.generate_trading_calendar(use_cache=not args.no_cache)
            print(f"Trading calendar: {len(df)} rows")


if __name__ == "__main__":
    main()
