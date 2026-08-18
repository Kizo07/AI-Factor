"""ETF AUM Fetching Pipeline.

Fetches ETF Assets Under Management data from Yahoo Finance.
Note: yfinance provides 'info' data which includes AUM for ETFs.
"""

import logging
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import yfinance as yf

from ..utils.config import get_config
from ..utils.storage import DataWriter, get_cache_key, load_cache, save_cache

logger = logging.getLogger(__name__)


class ETFAUMFetcher:
    """Fetches ETF AUM data from Yahoo Finance."""

    def __init__(self, config=None):
        """Initialize fetcher with configuration."""
        self.config = config or get_config()
        self.writer = DataWriter(self.config.raw_data_dir)
        self.cache_dir = self.config.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting (AUM fetches are lighter than returns)
        self.calls_made = 0
        self.calls_window_start = time.time()

    def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = time.time()
        window_elapsed = now - self.calls_window_start

        if window_elapsed > 3600:
            self.calls_made = 0
            self.calls_window_start = now

        if self.calls_made >= 1800:
            logger.warning("Rate limit reached, pausing for 60s")
            time.sleep(60)
            self.calls_made = 0
            self.calls_window_start = time.time()

    def _fetch_single_etf_aum(self, ticker: str) -> Optional[dict]:
        """
        Fetch AUM info for a single ETF.

        Note: Yahoo Finance info data provides total AUM, not historical daily AUM.
        For historical AUM, we'll need to use the forward-fill approach in the
        factor construction pipeline.

        Args:
            ticker: ETF ticker symbol

        Returns:
            Dictionary with AUM info or None if fetch fails
        """
        self._check_rate_limit()
        self.calls_made += 1

        try:
            logger.info(f"Fetching AUM info for {ticker}")

            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            if info is None or not info:
                logger.warning(f"No info data for {ticker}")
                return None

            # Extract relevant fields
            result = {
                "ticker": ticker,
                "fund_name": info.get("longName") or info.get("shortName"),
                "aum": info.get("totalAssets"),  # Total assets in USD
                "nav_price": info.get("navPrice"),
                "yield_value": info.get("yield"),
                "ytd_return": info.get("ytdReturn"),
                "three_year_avg_return": info.get("threeYearAverageReturn"),
                "five_year_avg_return": info.get("fiveYearAverageReturn"),
                "category": info.get("category"),
                "fund_family": info.get("fundFamily"),
                "legal_type": info.get("legalType"),
                "as_of_date": datetime.now().strftime("%Y-%m-%d"),  # Info is current
            }

            logger.info(f"Fetched AUM for {ticker}: ${result['aum']:,.0f}" if result["aum"] else f"No AUM data for {ticker}")
            return result

        except Exception as e:
            logger.error(f"Error fetching AUM for {ticker}: {e}")
            return None

    def fetch_current_aum(
        self,
        tickers: list[str],
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch current AUM for multiple ETFs.

        Args:
            tickers: List of ETF ticker symbols
            use_cache: Whether to use cached data

        Returns:
            DataFrame with AUM information
        """
        cache_key = get_cache_key(
            {
                "tickers": sorted(tickers),
                "function": "fetch_etf_aum_current",
            }
        )

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info(f"Loaded cached AUM data for {len(tickers)} ETFs")
                return cached

        results = []

        for ticker in tickers:
            aum_info = self._fetch_single_etf_aum(ticker)
            if aum_info is not None:
                results.append(aum_info)

            time.sleep(0.5)  # AUM fetches need more delay

        if not results:
            logger.error("No AUM data fetched for any ETF")
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # Save to cache
        if use_cache and self.config.data_sources.cache.enabled:
            save_cache(df, self.cache_dir, cache_key, suffix=".feather")

        # Save to raw data directory
        self.writer.write_feather(
            df,
            "etf_aum_current.feather",
            subfolder="etf_aum",
        )

        logger.info(f"Fetched AUM for {len(df)} ETFs")
        return df

    def fetch_from_classification_file(
        self,
        classification_path: Optional[object] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch AUM for all ETFs in the classification file.

        Args:
            classification_path: Path to ETF classification CSV
            use_cache: Whether to use cached data

        Returns:
            DataFrame with AUM information
        """
        if classification_path is None:
            classification_path = self.config.config_dir / "etf_classifications.csv"

        # Load classifications
        classifications = pd.read_csv(classification_path)

        # Filter to non-excluded ETFs
        active_etfs = classifications[
            classifications["bucket"].isin(["theme", "infra"])
        ]["ticker"].tolist()

        logger.info(f"Fetching AUM for {len(active_etfs)} active ETFs from classifications")

        return self.fetch_current_aum(
            tickers=active_etfs,
            use_cache=use_cache,
        )


def main():
    """CLI entry point for ETF AUM fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch ETF AUM from Yahoo Finance")
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="ETF tickers to fetch (if not provided, uses classification file)",
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    fetcher = ETFAUMFetcher()

    if args.tickers:
        data = fetcher.fetch_current_aum(
            tickers=args.tickers,
            use_cache=not args.no_cache,
        )
    else:
        data = fetcher.fetch_from_classification_file(use_cache=not args.no_cache)

    print(f"\nFetched AUM for {len(data)} ETFs")
    if not data.empty:
        print("\nAUM Summary:")
        print(data[["ticker", "fund_name", "aum"]].to_string(index=False))
        total_aum = data["aum"].sum()
        print(f"\nTotal AUM: ${total_aum:,.0f}")


if __name__ == "__main__":
    main()
