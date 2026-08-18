"""Configuration management for AI Factor Suite."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field


class YahooFinanceConfig(BaseModel):
    """Yahoo Finance configuration."""

    enabled: bool = True
    rate_limit_calls: int = 1800
    rate_limit_pause: int = 60


class FredConfig(BaseModel):
    """FRED (Federal Reserve) configuration."""

    enabled: bool = True
    api_key: Optional[str] = None
    base_url: str = "https://api.stlouisfed.org/fred"


class FamaFrenchConfig(BaseModel):
    """Fama-French data library configuration."""

    enabled: bool = True
    base_url: str = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"


class AlphaVantageConfig(BaseModel):
    """Alpha Vantage configuration."""

    enabled: bool = False
    api_key: Optional[str] = None
    base_url: str = "https://www.alphavantage.co"
    calls_per_day: int = 25
    calls_per_minute: int = 5


class IEXCloudConfig(BaseModel):
    """IEX Cloud configuration."""

    enabled: bool = False
    api_key: Optional[str] = None
    base_url: str = "https://cloud.iexapis.com"


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    directory: str = "data/cache"
    etf_returns_ttl: int = 86400  # 1 day
    etf_aum_ttl: int = 604800  # 1 week
    reference_ttl: int = 2592000  # 30 days


class DataSourcesConfig(BaseModel):
    """Data sources configuration."""

    yahoo_finance: YahooFinanceConfig = Field(default_factory=YahooFinanceConfig)
    fred: FredConfig = Field(default_factory=FredConfig)
    fama_french: FamaFrenchConfig = Field(default_factory=FamaFrenchConfig)
    alpha_vantage: AlphaVantageConfig = Field(default_factory=AlphaVantageConfig)
    iex_cloud: IEXCloudConfig = Field(default_factory=IEXCloudConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)


class Config(BaseModel):
    """Main application configuration."""

    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    config_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "config")

    data_sources: DataSourcesConfig = Field(default_factory=DataSourcesConfig)

    # Paths
    raw_data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "raw")
    processed_data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "processed")
    factors_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "factors")
    reference_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "reference")
    diagnostics_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data" / "diagnostics")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Factor construction parameters
    monthly_rebalance: bool = True
    max_aum_staleness_days: int = 60
    max_single_etf_weight: Optional[float] = None  # None = no cap, 0.33 = 33% cap


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to data_sources.yaml. If None, uses default location.

    Returns:
        Config object with loaded settings.
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "data_sources.yaml"

    # Load YAML config
    if config_path.exists():
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
    else:
        yaml_config = {}

    # Create base config
    data_sources_config = DataSourcesConfig(**yaml_config.get("data_sources", {}))

    # Load environment variables for API keys
    if data_sources_config.fred.enabled:
        data_sources_config.fred.api_key = os.getenv("FRED_API_KEY")

    if data_sources_config.alpha_vantage.enabled:
        data_sources_config.alpha_vantage.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    if data_sources_config.iex_cloud.enabled:
        data_sources_config.iex_cloud.api_key = os.getenv("IEX_API_KEY")

    config = Config(data_sources=data_sources_config)

    # Create data directories
    for dir_path in [
        config.raw_data_dir,
        config.processed_data_dir,
        config.factors_dir,
        config.reference_dir,
        config.diagnostics_dir,
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)

    return config


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance (lazy loading)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
