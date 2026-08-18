"""ETF Returns Fetching Pipeline.

Fetches daily ETF total/adjusted returns from Yahoo Finance using yfinance.
Implements caching, rate limiting, and basic validation.
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

from ..utils.config import get_config
from ..utils.storage import DataWriter, get_cache_key, load_cache, save_cache
from ..utils.validation import validate_returns

logger = logging.getLogger(__name__)


class ETFReturnsFetcher:
    """Fetches ETF returns data from Yahoo Finance."""

    def __init__(self, config=None):
        """Initialize fetcher with configuration."""
        self.config = config or get_config()
        self.writer = DataWriter(self.config.raw_data_dir)
        self.cache_dir = self.config.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting
        self.calls_made = 0
        self.calls_window_start = time.time()
        self.rate_limit_calls = self.config.data_sources.yahoo_finance.rate_limit_calls
        self.rate_limit_pause = self.config.data_sources.yahoo_finance.rate_limit_pause

    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = time.time()
        window_elapsed = now - self.calls_window_start

        # Reset counter if window has passed
        if window_elapsed > 3600:  # 1 hour window
            self.calls_made = 0
            self.calls_window_start = now

        # Pause if approaching limit
        if self.calls_made >= self.rate_limit_calls:
            logger.warning(f"Rate limit reached, pausing for {self.rate_limit_pause}s")
            time.sleep(self.rate_limit_pause)
            self.calls_made = 0
            self.calls_window_start = time.time()

    def _fetch_single_etf(
        self,
        ticker: str,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch returns for a single ETF.

        Args:
            ticker: ETF ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today

        Returns:
            DataFrame with columns: date, open, high, low, close, adj_close, volume, return
            or None if fetch fails
        """
        self._check_rate_limit()
        self.calls_made += 1

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        try:
            logger.info(f"Fetching {ticker} from {start_date} to {end_date}")

            # Fetch from yfinance
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(start=start_date, end=end_date)

            if hist.empty:
                logger.warning(f"No data returned for {ticker}")
                return None

            # Reset index to get date as column
            hist = hist.reset_index()

            # Standardize column names
            hist.columns = [str(c).lower().replace(" ", "_") for c in hist.columns]

            # Rename to standard names
            column_map = {
                "date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "adj_close": "adj_close",
                "volume": "volume",
            }
            hist = hist.rename(columns={k: v for k, v in column_map.items() if k in hist.columns})

            # Ensure date is datetime
            if "date" in hist.columns:
                hist["date"] = pd.to_datetime(hist["date"])

            # Calculate returns (fill_method=None: do not silently pad prices)
            if "adj_close" in hist.columns:
                hist["return"] = hist["adj_close"].pct_change(fill_method=None)
            elif "close" in hist.columns:
                hist["return"] = hist["close"].pct_change(fill_method=None)
            else:
                logger.error(f"No price data found for {ticker}")
                return None

            # Add ticker column
            hist["ticker"] = ticker

            # Add data quality flag
            hist["data_quality_flag"] = "ok"

            # Select and order columns
            cols = [
                "date",
                "ticker",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
                "return",
                "data_quality_flag",
            ]
            hist = hist[[c for c in cols if c in hist.columns]]

            logger.info(f"Fetched {len(hist)} rows for {ticker}")
            return hist

        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return None

    def fetch(
        self,
        tickers: list[str],
        start_date: str,
        end_date: Optional[str] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch returns for multiple ETFs.

        Args:
            tickers: List of ETF ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
            use_cache: Whether to use cached data

        Returns:
            DataFrame with all ETF returns
        """
        cache_key = get_cache_key(
            {
                "tickers": sorted(tickers),
                "start_date": start_date,
                "end_date": end_date,
                "function": "fetch_etf_returns",
            }
        )

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info(f"Loaded cached data for {len(tickers)} ETFs")
                return cached

        results = []

        for ticker in tickers:
            etf_data = self._fetch_single_etf(ticker, start_date, end_date)
            if etf_data is not None:
                results.append(etf_data)

            # Small delay to be respectful
            time.sleep(0.2)

        if not results:
            logger.error("No data fetched for any ETF")
            return pd.DataFrame()

        # Combine all results
        combined = pd.concat(results, ignore_index=True)

        # Validate
        validation = validate_returns(combined)
        if not validation.passed:
            logger.warning(f"Validation issues: {validation.message}")

        # Save to cache
        if use_cache and self.config.data_sources.cache.enabled:
            save_cache(combined, self.cache_dir, cache_key, suffix=".feather")

        # Save to raw data directory
        self.writer.write_feather(
            combined,
            "etf_returns.feather",
            subfolder="etf_returns",
        )

        logger.info(f"Fetched {len(combined)} total rows for {len(tickers)} ETFs")
        return combined

    def fetch_with_retry(
        self,
        tickers: list[str],
        start_date: str,
        end_date: Optional[str] = None,
        max_retries: int = 3,
    ) -> pd.DataFrame:
        """
        Fetch returns with retry logic for failed tickers.

        Args:
            tickers: List of ETF ticker symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            max_retries: Maximum retry attempts for failed tickers

        Returns:
            DataFrame with all ETF returns
        """
        all_results = []
        failed_tickers = set(tickers)
        retry_count = 0

        while failed_tickers and retry_count < max_retries:
            retry_count += 1
            logger.info(f"Fetch attempt {retry_count}, {len(failed_tickers)} remaining")

            current_results = []
            still_failed = set()

            for ticker in failed_tickers:
                etf_data = self._fetch_single_etf(ticker, start_date, end_date)
                if etf_data is not None:
                    current_results.append(etf_data)
                else:
                    still_failed.add(ticker)

                time.sleep(0.2)

            all_results.extend(current_results)
            failed_tickers = still_failed

            if failed_tickers:
                wait_time = 5 * retry_count  # Exponential backoff
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        if failed_tickers:
            logger.warning(f"Failed to fetch {len(failed_tickers)} tickers after {max_retries} retries")

        if all_results:
            combined = pd.concat(all_results, ignore_index=True)
            self.writer.write_feather(
                combined,
                "etf_returns.feather",
                subfolder="etf_returns",
            )
            return combined

        return pd.DataFrame()

    def fetch_from_classification_file(
        self,
        classification_path: Optional[Path] = None,
        start_date: str = "2010-01-01",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch returns for all ETFs in the classification file.

        Args:
            classification_path: Path to ETF classification CSV
            start_date: Start date for returns
            use_cache: Whether to use cached data

        Returns:
            DataFrame with all ETF returns
        """
        if classification_path is None:
            classification_path = self.config.config_dir / "etf_classifications.csv"

        # Load classifications
        classifications = pd.read_csv(classification_path)

        # Filter to non-excluded ETFs
        active_etfs = classifications[
            classifications["bucket"].isin(["theme", "infra"])
        ]["ticker"].tolist()

        logger.info(f"Fetching returns for {len(active_etfs)} active ETFs from classifications")

        return self.fetch(
            tickers=active_etfs,
            start_date=start_date,
            use_cache=use_cache,
        )


def main():
    """CLI entry point for ETF returns fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch ETF returns from Yahoo Finance")
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="ETF tickers to fetch (if not provided, uses classification file)",
    )
    parser.add_argument("--start-date", default="2010-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    fetcher = ETFReturnsFetcher()

    if args.tickers:
        data = fetcher.fetch(
            tickers=args.tickers,
            start_date=args.start_date,
            end_date=args.end_date,
            use_cache=not args.no_cache,
        )
    else:
        data = fetcher.fetch_from_classification_file(
            start_date=args.start_date,
            use_cache=not args.no_cache,
        )

    print(f"\nFetched {len(data)} rows")
    if not data.empty:
        print(f"Date range: {data['date'].min()} to {data['date'].max()}")
        print(f"Tickers: {sorted(data['ticker'].unique())}")


if __name__ == "__main__":
    main()
