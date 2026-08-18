"""Tests for data pipelines."""

import pytest
import pandas as pd
from datetime import datetime


class TestETFReturnsFetcher:
    """Tests for ETF returns fetching."""

    def test_fetcher_initialization(self):
        """Test that fetcher can be initialized."""
        from src.pipelines.fetch_etf_returns import ETFReturnsFetcher

        fetcher = ETFReturnsFetcher()
        assert fetcher is not None
        assert fetcher.config is not None

    def test_single_etf_fetch(self, monkeypatch):
        """Test fetching a single ETF (mocked)."""
        # This would be a mocked test in real implementation
        pass


class TestValidation:
    """Tests for validation utilities."""

    def test_validate_returns_empty(self):
        """Test validation with empty DataFrame."""
        from src.utils.validation import validate_returns

        df = pd.DataFrame()
        result = validate_returns(df)
        assert not result.passed
        assert "empty" in result.message.lower()

    def test_validate_returns_missing_column(self):
        """Test validation with missing return column."""
        from src.utils.validation import validate_returns

        df = pd.DataFrame({"date": [1, 2, 3]})
        result = validate_returns(df)
        assert not result.passed
        assert "return" in result.message

    def test_validate_returns_valid(self):
        """Test validation with valid returns."""
        from src.utils.validation import validate_returns

        df = pd.DataFrame({
            "return": [0.01, 0.02, -0.01, 0.005, -0.003]
        })
        result = validate_returns(df)
        assert result.passed

    def test_validate_returns_extreme(self):
        """Test validation detects extreme returns."""
        from src.utils.validation import validate_returns

        df = pd.DataFrame({
            "return": [0.01, 0.02, -0.01, 0.30]  # 30% return
        })
        result = validate_returns(df, max_daily_return=0.25)
        assert not result.passed
        assert "extreme" in result.message.lower()


class TestConfig:
    """Tests for configuration."""

    def test_config_load(self):
        """Test configuration loading."""
        from src.utils.config import load_config

        config = load_config()
        assert config is not None
        assert config.project_root is not None

    def test_config_paths(self):
        """Test config paths are set correctly."""
        from src.utils.config import get_config

        config = get_config()
        assert config.data_dir.exists()
        assert config.config_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
