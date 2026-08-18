"""Main entry point for AI Factor Suite data pipeline."""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pipelines.fetch_etf_returns import ETFReturnsFetcher
from src.pipelines.fetch_etf_aum import ETFAUMFetcher
from src.pipelines.fetch_reference_data import ReferenceDataFetcher
from src.pipelines.construct_factors import FactorConstructor
from src.utils.config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_etf_data(args):
    """Fetch ETF returns and AUM data."""
    config = get_config()

    if args.returns or args.all:
        logger.info("Fetching ETF returns...")
        fetcher = ETFReturnsFetcher(config)
        data = fetcher.fetch_from_classification_file(
            start_date=args.start_date or "2010-01-01",
            use_cache=not args.no_cache,
        )
        logger.info(f"Fetched {len(data)} rows of ETF returns")

    if args.aum or args.all:
        logger.info("Fetching ETF AUM...")
        fetcher = ETFAUMFetcher(config)
        data = fetcher.fetch_from_classification_file(use_cache=not args.no_cache)
        logger.info(f"Fetched AUM for {len(data)} ETFs")


def fetch_reference_data(args):
    """Fetch reference data (FF factors, risk-free rate, trading calendar)."""
    config = get_config()
    fetcher = ReferenceDataFetcher(config)

    if args.ff or args.all:
        logger.info("Fetching Fama-French factors...")
        data = fetcher.merge_ff_factors(use_cache=not args.no_cache)
        logger.info(f"Fetched {len(data)} rows of FF factors (monthly)")
        data_daily = fetcher.merge_ff_factors(use_cache=not args.no_cache, daily=True)
        logger.info(f"Fetched {len(data_daily)} rows of FF factors (daily)")

    if args.rf or args.all:
        logger.info("Fetching risk-free rate...")
        data = fetcher.fetch_risk_free_rate(use_cache=not args.no_cache)
        logger.info(f"Fetched {len(data)} rows of risk-free rate")

    if args.calendar or args.all:
        logger.info("Generating trading calendar...")
        data = fetcher.generate_trading_calendar(use_cache=not args.no_cache)
        logger.info(f"Generated {len(data)} days of trading calendar")


def construct_factors(args):
    """Construct AI factors from fetched data."""
    config = get_config()
    constructor = FactorConstructor(config)

    logger.info("Constructing AI factors...")
    factors = constructor.construct_factors()

    if factors.empty:
        logger.error("Failed to construct factors")
        return

    logger.info(f"Constructed {len(factors)} days of AI factors")
    logger.info(f"Date range: {factors['date'].min()} to {factors['date'].max()}")

    if not args.no_diagnostics:
        logger.info("Computing diagnostics...")
        # Load FF factors if available — prefer the daily series, since the AI
        # factors are daily; fall back to monthly if daily has not been fetched.
        ff_daily_path = config.reference_dir / "ff_factors_daily.feather"
        ff_monthly_path = config.reference_dir / "ff_factors.feather"
        if ff_daily_path.exists():
            ff_factors = pd.read_feather(ff_daily_path)
        elif ff_monthly_path.exists():
            ff_factors = pd.read_feather(ff_monthly_path)
        else:
            ff_factors = None

        diagnostics = constructor.compute_diagnostics(factors, ff_factors)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Factor Suite - Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main fetch --all              # Fetch all data
  python -m src.main fetch --returns --aum    # Fetch ETF data only
  python -m src.main reference --all          # Fetch reference data
  python -m src.main construct                # Construct factors
  python -m src.main all                      # Run full pipeline
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch ETF data")
    fetch_parser.add_argument("--returns", action="store_true", help="Fetch ETF returns")
    fetch_parser.add_argument("--aum", action="store_true", help="Fetch ETF AUM")
    fetch_parser.add_argument("--all", action="store_true", help="Fetch all ETF data")
    fetch_parser.add_argument("--start-date", help="Start date for returns (YYYY-MM-DD)")
    fetch_parser.add_argument("--no-cache", action="store_true", help="Disable cache")

    # Reference command
    ref_parser = subparsers.add_parser("reference", help="Fetch reference data")
    ref_parser.add_argument("--ff", action="store_true", help="Fetch Fama-French factors")
    ref_parser.add_argument("--rf", action="store_true", help="Fetch risk-free rate")
    ref_parser.add_argument("--calendar", action="store_true", help="Generate trading calendar")
    ref_parser.add_argument("--all", action="store_true", help="Fetch all reference data")
    ref_parser.add_argument("--no-cache", action="store_true", help="Disable cache")

    # Construct command
    construct_parser = subparsers.add_parser("construct", help="Construct AI factors")
    construct_parser.add_argument("--no-diagnostics", action="store_true", help="Skip diagnostics")

    # All command
    all_parser = subparsers.add_parser("all", help="Run full pipeline")
    all_parser.add_argument("--start-date", default="2010-01-01", help="Start date for returns")
    all_parser.add_argument("--no-cache", action="store_true", help="Disable cache")
    all_parser.add_argument("--no-diagnostics", action="store_true", help="Skip diagnostics")

    args = parser.parse_args()

    if args.command == "fetch":
        fetch_etf_data(args)
    elif args.command == "reference":
        fetch_reference_data(args)
    elif args.command == "construct":
        construct_factors(args)
    elif args.command == "all":
        # Run full pipeline
        fetch_args = argparse.Namespace(
            returns=True, aum=True, all=True, start_date=args.start_date, no_cache=args.no_cache
        )
        fetch_etf_data(fetch_args)

        ref_args = argparse.Namespace(
            ff=True, rf=True, calendar=True, all=True, no_cache=args.no_cache
        )
        fetch_reference_data(ref_args)

        construct_args = argparse.Namespace(no_diagnostics=args.no_diagnostics)
        construct_factors(construct_args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
