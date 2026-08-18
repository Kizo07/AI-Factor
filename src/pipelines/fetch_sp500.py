"""S&P 500 Data Pipeline.

Fetches:
1. S&P 500 constituent list from Wikipedia (ticker, name, GICS sector,
   GICS sub-industry), with tickers converted to Yahoo Finance format.
2. Daily adjusted prices / simple returns for all constituents via yfinance
   (batched downloads to avoid multi-ticker flakiness).
"""

import logging
import time
from datetime import datetime, timedelta
from io import StringIO
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

from ..utils.config import get_config
from ..utils.storage import DataWriter, get_cache_key, load_cache, save_cache

logger = logging.getLogger(__name__)

WIKIPEDIA_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


class SP500ConstituentFetcher:
    """Fetches the S&P 500 constituent table from Wikipedia."""

    def __init__(self, config=None):
        """Initialize fetcher with configuration."""
        self.config = config or get_config()
        self.writer = DataWriter(self.config.raw_data_dir)
        self.cache_dir = self.config.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetch the S&P 500 constituent list.

        Args:
            use_cache: Whether to use cached data

        Returns:
            DataFrame with columns: ticker, name, gics_sector, gics_sub_industry
            (tickers converted to Yahoo format, e.g. BRK.B -> BRK-B)
        """
        cache_key = get_cache_key({"function": "fetch_sp500_constituents"})

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info(f"Loaded cached S&P 500 constituents ({len(cached)} rows)")
                return cached

        try:
            logger.info(f"Fetching S&P 500 constituents from {WIKIPEDIA_SP500_URL}")
            # requests handles certificates that urllib (pd.read_html default) cannot
            response = requests.get(
                WIKIPEDIA_SP500_URL,
                timeout=60,
                headers={"User-Agent": "Mozilla/5.0 (AI-Factor research)"},
            )
            response.raise_for_status()
            tables = pd.read_html(StringIO(response.text))
            constituents = tables[0]

            constituents = constituents.rename(
                columns={
                    "Symbol": "ticker",
                    "Security": "name",
                    "GICS Sector": "gics_sector",
                    "GICS Sub-Industry": "gics_sub_industry",
                }
            )
            constituents = constituents[
                ["ticker", "name", "gics_sector", "gics_sub_industry"]
            ].copy()

            # Convert tickers to Yahoo Finance format (BRK.B -> BRK-B)
            constituents["ticker"] = constituents["ticker"].str.replace(".", "-", regex=False)

            # Save to cache
            if use_cache and self.config.data_sources.cache.enabled:
                save_cache(constituents, self.cache_dir, cache_key, suffix=".feather")

            # Save to raw data directory
            self.writer.write_feather(
                constituents,
                "sp500_constituents.feather",
                subfolder="sp500",
            )

            logger.info(f"Fetched {len(constituents)} S&P 500 constituents")
            return constituents

        except Exception as e:
            logger.error(f"Error fetching S&P 500 constituents: {e}")
            return pd.DataFrame()


class StockReturnsFetcher:
    """Fetches daily adjusted prices and returns for a list of stocks."""

    def __init__(self, config=None):
        """Initialize fetcher with configuration."""
        self.config = config or get_config()
        self.writer = DataWriter(self.config.raw_data_dir)
        self.cache_dir = self.config.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.failed_tickers: list[str] = []

    def _fetch_batch(
        self,
        tickers: list[str],
        start_date: str,
        end_date: Optional[str] = None,
    ) -> list[pd.DataFrame]:
        """
        Fetch adjusted prices for one batch of tickers via yf.download.

        Args:
            tickers: List of ticker symbols (one batch)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today

        Returns:
            List of per-ticker DataFrames (date, ticker, adj_close, return)
        """
        results = []

        try:
            logger.info(f"Fetching batch of {len(tickers)} tickers")
            data = yf.download(
                tickers,
                start=start_date,
                end=end_date,
                auto_adjust=True,
                threads=True,
                progress=False,
            )

            if data.empty:
                logger.warning(f"No data returned for batch: {tickers[:5]}...")
                self.failed_tickers.extend(tickers)
                return results

            # yf.download with multiple tickers returns MultiIndex columns
            # ('Close', ticker); a single ticker returns flat columns.
            if isinstance(data.columns, pd.MultiIndex):
                if "Close" not in data.columns.get_level_values(0):
                    logger.warning("No 'Close' level in downloaded data")
                    self.failed_tickers.extend(tickers)
                    return results
                close = data["Close"]
            else:
                close = data[["Close"]].rename(columns={"Close": tickers[0]})

            close.index = pd.to_datetime(close.index, utc=True).tz_localize(None).normalize()

            for ticker in tickers:
                if ticker not in close.columns:
                    logger.warning(f"Ticker {ticker} missing from batch result")
                    self.failed_tickers.append(ticker)
                    continue

                prices = close[ticker].dropna()
                if prices.empty:
                    logger.warning(f"No price data for {ticker}")
                    self.failed_tickers.append(ticker)
                    continue

                ticker_df = pd.DataFrame(
                    {
                        "date": prices.index,
                        "ticker": ticker,
                        "adj_close": prices.values,
                    }
                )
                # fill_method=None: do not silently pad prices
                ticker_df["return"] = ticker_df["adj_close"].pct_change(fill_method=None)
                results.append(ticker_df)

        except Exception as e:
            logger.error(f"Error fetching batch {tickers[:5]}...: {e}")
            self.failed_tickers.extend(tickers)

        return results

    def fetch(
        self,
        tickers: list[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        years: int = 2,
        batch_size: int = 100,
        use_cache: bool = True,
        filename: str = "sp500_returns.feather",
    ) -> pd.DataFrame:
        """
        Fetch daily returns for multiple stocks in batches.

        Args:
            tickers: List of ticker symbols
            start_date: Start date (YYYY-MM-DD); defaults to `years` ago
            end_date: End date (YYYY-MM-DD), defaults to today
            years: Lookback in years if start_date is not given
            batch_size: Number of tickers per yf.download call
            use_cache: Whether to use cached data
            filename: Output filename under data/raw/sp500/

        Returns:
            Long-format DataFrame with columns: date, ticker, adj_close, return
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365 * years + 10)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        cache_key = get_cache_key(
            {
                "tickers": sorted(tickers),
                "start_date": start_date,
                "end_date": end_date,
                "function": "fetch_sp500_returns",
            }
        )

        if use_cache:
            cached = load_cache(self.cache_dir, cache_key, suffix=".feather")
            if cached is not None:
                logger.info(f"Loaded cached stock returns ({len(cached)} rows)")
                return cached

        self.failed_tickers = []
        results = []

        batches = [tickers[i : i + batch_size] for i in range(0, len(tickers), batch_size)]
        logger.info(f"Fetching {len(tickers)} tickers in {len(batches)} batches")

        for batch in batches:
            results.extend(self._fetch_batch(batch, start_date, end_date))
            # Small delay between batches to be respectful
            time.sleep(0.5)

        if not results:
            logger.error("No data fetched for any ticker")
            return pd.DataFrame()

        combined = pd.concat(results, ignore_index=True)
        combined["date"] = pd.to_datetime(combined["date"], utc=True).dt.tz_localize(
            None
        ).dt.normalize()
        combined = combined[["date", "ticker", "adj_close", "return"]]

        if self.failed_tickers:
            logger.warning(
                f"Failed to fetch {len(self.failed_tickers)} tickers: "
                f"{sorted(set(self.failed_tickers))}"
            )

        # Save to cache
        if use_cache and self.config.data_sources.cache.enabled:
            save_cache(combined, self.cache_dir, cache_key, suffix=".feather")

        # Save to raw data directory
        self.writer.write_feather(
            combined,
            filename,
            subfolder="sp500",
        )

        logger.info(
            f"Fetched {len(combined)} rows for "
            f"{combined['ticker'].nunique()} tickers "
            f"({combined['date'].min().date()} to {combined['date'].max().date()})"
        )
        return combined


def main():
    """CLI entry point for S&P 500 data fetching."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch S&P 500 constituents and returns")
    parser.add_argument(
        "--constituents-only",
        action="store_true",
        help="Only fetch the constituent list",
    )
    parser.add_argument("--years", type=int, default=2, help="Years of price history")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--batch-size", type=int, default=100, help="Tickers per batch")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    constituent_fetcher = SP500ConstituentFetcher()
    constituents = constituent_fetcher.fetch(use_cache=not args.no_cache)

    if constituents.empty:
        print("Failed to fetch constituents")
        return

    print(f"\nConstituents: {len(constituents)}")
    print(constituents.head())

    if args.constituents_only:
        return

    returns_fetcher = StockReturnsFetcher()
    data = returns_fetcher.fetch(
        tickers=constituents["ticker"].tolist(),
        start_date=args.start_date,
        end_date=args.end_date,
        years=args.years,
        batch_size=args.batch_size,
        use_cache=not args.no_cache,
    )

    print(f"\nFetched {len(data)} rows")
    if not data.empty:
        print(f"Date range: {data['date'].min()} to {data['date'].max()}")
        print(f"Tickers: {data['ticker'].nunique()}")
        print(f"Failed: {sorted(set(returns_fetcher.failed_tickers))}")


if __name__ == "__main__":
    main()
