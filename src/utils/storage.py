"""Storage utilities for AI Factor Suite."""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Optional, Union

import pandas as pd


def get_cache_key(data: Any) -> str:
    """Generate a cache key from data."""
    if isinstance(data, (dict, list, str, int, float, bool)):
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return hashlib.md5(str(data).encode()).hexdigest()


def cache_path(
    cache_dir: Path,
    key: str,
    suffix: str = ".feather",
) -> Path:
    """Get cache file path for a given key."""
    return cache_dir / f"{key}{suffix}"


def save_cache(
    data: Any,
    cache_dir: Path,
    key: str,
    suffix: str = ".feather",
) -> None:
    """Save data to cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache_dir, key, suffix)

    if suffix == ".feather":
        if isinstance(data, pd.DataFrame):
            data.to_feather(path)
        else:
            raise ValueError("Feather cache requires DataFrame")
    else:
        with open(path, "wb") as f:
            pickle.dump(data, f)


def load_cache(
    cache_dir: Path,
    key: str,
    suffix: str = ".feather",
) -> Optional[Any]:
    """Load data from cache. Returns None if not found."""
    path = cache_path(cache_dir, key, suffix)

    if not path.exists():
        return None

    if suffix == ".feather":
        return pd.read_feather(path)
    else:
        with open(path, "rb") as f:
            return pickle.load(f)


def clear_cache(
    cache_dir: Path,
    key: Optional[str] = None,
) -> None:
    """Clear cache. If key is None, clear all cache."""
    if key is None:
        # Clear all cache
        for path in cache_dir.glob("*"):
            path.unlink()
    else:
        # Clear specific cache (try all suffixes)
        for suffix in [".feather", ".pkl"]:
            path = cache_path(cache_dir, key, suffix)
            if path.exists():
                path.unlink()


class DataWriter:
    """Helper class for writing data to standardized locations."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write_feather(
        self,
        data: pd.DataFrame,
        filename: str,
        subfolder: Optional[str] = None,
    ) -> Path:
        """Write DataFrame to Feather format."""
        if subfolder:
            path = self.base_dir / subfolder
            path.mkdir(parents=True, exist_ok=True)
            path = path / filename
        else:
            path = self.base_dir / filename

        # Ensure filename has .feather extension
        if not str(path).endswith(".feather"):
            path = path.with_suffix(".feather")

        data.to_feather(path)
        return path

    def write_csv(
        self,
        data: pd.DataFrame,
        filename: str,
        subfolder: Optional[str] = None,
    ) -> Path:
        """Write DataFrame to CSV (legacy method for compatibility)."""
        if subfolder:
            path = self.base_dir / subfolder
            path.mkdir(parents=True, exist_ok=True)
            path = path / filename
        else:
            path = self.base_dir / filename

        data.to_csv(path, index=False)
        return path

    def write_parquet(
        self,
        data: pd.DataFrame,
        filename: str,
        subfolder: Optional[str] = None,
    ) -> Path:
        """Write DataFrame to Parquet format."""
        if subfolder:
            path = self.base_dir / subfolder
            path.mkdir(parents=True, exist_ok=True)
            path = path / filename
        else:
            path = self.base_dir / filename

        data.to_parquet(path, index=False)
        return path


class DataLoader:
    """Helper class for loading data from standardized locations."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def load_feather(
        self,
        filename: str,
        subfolder: Optional[str] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Load DataFrame from Feather format."""
        if subfolder:
            path = self.base_dir / subfolder / filename
        else:
            path = self.base_dir / filename

        # Ensure filename has .feather extension
        if not str(path).endswith(".feather"):
            path = path.with_suffix(".feather")

        return pd.read_feather(path, **kwargs)

    def load_csv(
        self,
        filename: str,
        subfolder: Optional[str] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Load DataFrame from CSV (legacy method for compatibility)."""
        if subfolder:
            path = self.base_dir / subfolder / filename
        else:
            path = self.base_dir / filename

        return pd.read_csv(path, **kwargs)

    def load_parquet(
        self,
        filename: str,
        subfolder: Optional[str] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Load DataFrame from Parquet format."""
        if subfolder:
            path = self.base_dir / subfolder / filename
        else:
            path = self.base_dir / filename

        return pd.read_parquet(path, **kwargs)

    def list_files(
        self,
        subfolder: Optional[str] = None,
        pattern: str = "*",
    ) -> list[Path]:
        """List files in directory."""
        if subfolder:
            path = self.base_dir / subfolder
        else:
            path = self.base_dir

        if not path.exists():
            return []

        return list(path.glob(pattern))
