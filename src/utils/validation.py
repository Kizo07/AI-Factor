"""Validation utilities for AI Factor Suite."""

from datetime import timedelta
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Result of a validation check."""

    check_name: str
    passed: bool
    message: str
    details: dict = Field(default_factory=dict)


def validate_returns(df: pd.DataFrame, max_daily_return: float = 0.25) -> ValidationResult:
    """
    Validate returns data.

    Args:
        df: DataFrame with 'return' column
        max_daily_return: Maximum acceptable daily return (default 25%)

    Returns:
        ValidationResult with check results
    """
    if df.empty:
        return ValidationResult(
            check_name="validate_returns",
            passed=False,
            message="DataFrame is empty",
        )

    if "return" not in df.columns:
        return ValidationResult(
            check_name="validate_returns",
            passed=False,
            message="Missing 'return' column",
        )

    # Check for extreme returns
    extreme_returns = df[np.abs(df["return"]) > max_daily_return]

    if len(extreme_returns) > 0:
        return ValidationResult(
            check_name="validate_returns",
            passed=False,
            message=f"Found {len(extreme_returns)} extreme returns (>{max_daily_return*100:.0f}%)",
            details={
                "extreme_count": len(extreme_returns),
                "extreme_examples": extreme_returns.head(5).to_dict("records"),
            },
        )

    # Check for missing values
    missing_count = df["return"].isna().sum()
    if missing_count > 0:
        return ValidationResult(
            check_name="validate_returns",
            passed=True,  # Warning only
            message=f"{missing_count} missing returns found",
            details={"missing_count": missing_count},
        )

    return ValidationResult(
        check_name="validate_returns",
        passed=True,
        message="All validation checks passed",
        details={"row_count": len(df)},
    )


def validate_point_in_time(
    df: pd.DataFrame,
    inception_col: str,
    date_col: str,
) -> ValidationResult:
    """
    Validate point-in-time data integrity.

    Ensures no data exists before inception dates.

    Args:
        df: DataFrame with date and inception columns
        inception_col: Name of column with inception dates
        date_col: Name of column with observation dates

    Returns:
        ValidationResult with check results
    """
    required_cols = {date_col, inception_col}
    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        return ValidationResult(
            check_name="validate_point_in_time",
            passed=False,
            message=f"Missing required columns: {missing_cols}",
        )

    # Merge inception dates and check for violations
    df_merged = df.merge(
        df[[date_col, inception_col]].drop_duplicates(),
        on=date_col,
        how="left",
    )

    # Check for observations before inception
    if inception_col in df_merged.columns:
        pre_inception = df_merged[df_merged[date_col] < df_merged[inception_col]]
        if len(pre_inception) > 0:
            return ValidationResult(
                check_name="validate_point_in_time",
                passed=False,
                message=f"Found {len(pre_inception)} observations before inception",
                details={"pre_inception_count": len(pre_inception)},
            )

    return ValidationResult(
        check_name="validate_point_in_time",
        passed=True,
        message="Point-in-time integrity validated",
        details={"row_count": len(df)},
    )


def validate_weights(
    df: pd.DataFrame,
    weight_col: str = "weight",
    group_col: Optional[str] = None,
    tolerance: float = 1e-6,
    max_weight: Optional[float] = None,
) -> ValidationResult:
    """
    Validate weight sums and concentration.

    Args:
        df: DataFrame with weight column
        weight_col: Name of weight column
        group_col: If provided, check weights within groups (e.g., by date)
        tolerance: Tolerance for weight sum check
        max_weight: If provided, check that no single weight exceeds this

    Returns:
        ValidationResult with check results
    """
    if weight_col not in df.columns:
        return ValidationResult(
            check_name="validate_weights",
            passed=False,
            message=f"Missing weight column: {weight_col}",
        )

    details = {}

    # Check for negative weights
    negative_weights = df[df[weight_col] < 0]
    if len(negative_weights) > 0:
        return ValidationResult(
            check_name="validate_weights",
            passed=False,
            message=f"Found {len(negative_weights)} negative weights",
            details={"negative_count": len(negative_weights)},
        )

    # Check weight sums
    if group_col:
        weight_sums = df.groupby(group_col)[weight_col].sum()
        bad_sums = weight_sums[(weight_sums < 1 - tolerance) | (weight_sums > 1 + tolerance)]

        if len(bad_sums) > 0:
            return ValidationResult(
                check_name="validate_weights",
                passed=False,
                message=f"Weight sums not equal to 1 for {len(bad_sums)} groups",
                details={"bad_groups": bad_sums.head(10).to_dict()},
            )

        details["groups_checked"] = len(weight_sums)
    else:
        total_weight = df[weight_col].sum()
        if abs(total_weight - 1) > tolerance:
            return ValidationResult(
                check_name="validate_weights",
                passed=False,
                message=f"Total weight = {total_weight:.6f}, expected 1",
            )

    # Check concentration
    if max_weight is not None:
        max_actual = df[weight_col].max()
        if max_actual > max_weight:
            return ValidationResult(
                check_name="validate_weights",
                passed=False,
                message=f"Maximum weight {max_actual:.2%} exceeds limit {max_weight:.2%}",
                details={"max_weight": max_actual},
            )

    # Calculate HHI
    if group_col:
        hhis = df.groupby(group_col)[weight_col].apply(lambda w: (w**2).sum())
        details["avg_hhi"] = hhis.mean()
        details["max_hhi"] = hhis.max()

    return ValidationResult(
        check_name="validate_weights",
        passed=True,
        message="Weights validated",
        details=details,
    )


def validate_aum_staleness(
    df: pd.DataFrame,
    date_col: str,
    aum_date_col: str,
    max_staleness_days: int = 60,
) -> ValidationResult:
    """
    Validate AUM staleness (lag between observation date and AUM date).

    Args:
        df: DataFrame with dates and AUM dates
        date_col: Observation date column
        aum_date_col: AUM as-of date column
        max_staleness_days: Maximum allowed staleness in days

    Returns:
        ValidationResult with check results
    """
    required_cols = {date_col, aum_date_col}
    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        return ValidationResult(
            check_name="validate_aum_staleness",
            passed=False,
            message=f"Missing required columns: {missing_cols}",
        )

    # Calculate staleness
    df = df.copy()
    df["_staleness"] = (df[date_col] - df[aum_date_col]).dt.days

    stale = df[df["_staleness"] > max_staleness_days]

    if len(stale) > 0:
        return ValidationResult(
            check_name="validate_aum_staleness",
            passed=False,
            message=f"Found {len(stale)} stale AUM values (>{max_staleness_days} days)",
            details={
                "stale_count": len(stale),
                "max_staleness": df["_staleness"].max(),
            },
        )

    return ValidationResult(
        check_name="validate_aum_staleness",
        passed=True,
        message="AUM staleness validated",
        details={
            "max_staleness_days": df["_staleness"].max(),
            "avg_staleness_days": df["_staleness"].mean(),
        },
    )


def compute_diagnostics(
    returns: pd.Series,
    window_days: int = 252,
) -> dict:
    """
    Compute standard return diagnostics.

    Args:
        returns: Series of returns
        window_days: Rolling window for volatility calculations

    Returns:
        Dictionary with diagnostic metrics
    """
    if returns.empty:
        return {"error": "Empty returns series"}

    return {
        "count": len(returns),
        "mean": returns.mean(),
        "std": returns.std(),
        "min": returns.min(),
        "max": returns.max(),
        "skewness": returns.skew(),
        "kurtosis": returns.kurtosis(),
        "sharpe": returns.mean() / returns.std() if returns.std() > 0 else np.nan,
        "annualized_vol": returns.std() * np.sqrt(252),
        "rolling_vol_63d": returns.rolling(63).std().mean() * np.sqrt(252),
        "rolling_vol_126d": returns.rolling(126).std().mean() * np.sqrt(252),
        "rolling_vol_252d": returns.rolling(252).std().mean() * np.sqrt(252),
    }


def compute_correlation_diagnostics(
    df: pd.DataFrame,
    windows: list[int] = [63, 126, 252],
) -> dict:
    """
    Compute rolling correlation diagnostics between factors.

    Args:
        df: DataFrame with factor return columns
        windows: List of rolling window sizes

    Returns:
        Dictionary with correlation diagnostics
    """
    results = {}

    # Get numeric columns only
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Full sample correlations
    if len(numeric_cols) >= 2:
        full_corr = df[numeric_cols].corr()
        results["full_sample_correlations"] = full_corr.to_dict()

    # Rolling correlations
    for window in windows:
        if len(df) >= window:
            rolling_corr = df[numeric_cols].rolling(window).corr().dropna()
            results[f"rolling_{window}d_avg_correlation"] = rolling_corr.mean()

    return results


def check_factor_quality(
    factor_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> ValidationResult:
    """
    Basic quality check for factor returns.

    Args:
        factor_returns: Factor return series
        benchmark_returns: Benchmark return series (e.g., market)

    Returns:
        ValidationResult with quality metrics
    """
    if factor_returns.empty:
        return ValidationResult(
            check_name="check_factor_quality",
            passed=False,
            message="Empty factor returns",
        )

    details = {}

    # Basic stats
    details["mean_return"] = factor_returns.mean()
    details["volatility"] = factor_returns.std()
    details["annualized_vol"] = factor_returns.std() * np.sqrt(252)

    # Correlation with benchmark
    if not benchmark_returns.empty and len(factor_returns) == len(benchmark_returns):
        aligned_factor, aligned_bench = factor_returns.align(benchmark_returns, join="inner")
        if len(aligned_factor) > 0:
            details["correlation_with_benchmark"] = aligned_factor.corr(aligned_bench)

    # Check for extreme values
    extreme_threshold = 0.15  # 15%
    extreme_count = (np.abs(factor_returns) > extreme_threshold).sum()
    details["extreme_return_count"] = int(extreme_count)

    if extreme_count > 0:
        return ValidationResult(
            check_name="check_factor_quality",
            passed=True,  # Warning only
            message=f"Factor has {extreme_count} extreme returns",
            details=details,
        )

    return ValidationResult(
        check_name="check_factor_quality",
        passed=True,
        message="Factor quality checks passed",
        details=details,
    )
