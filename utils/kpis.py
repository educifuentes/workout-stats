"""
KPI calculation functions.

Computes key performance indicators like weekly, monthly, and yearly distance totals.
All functions operate on filtered DataFrames that respect user-selected date ranges and filters.
"""

import pandas as pd
from datetime import datetime, date, timedelta


def get_current_period_dates() -> tuple[date, date]:
    """
    Get date range for current week, month, and year calculations.
    
    Returns:
        Tuple of (start_date, end_date) for the current period
    """
    today = date.today()
    return (date.min, today)


def distance_this_week(df: pd.DataFrame) -> float:
    """
    Calculate total distance for the current week (Monday to Sunday).
    
    Args:
        df: Normalized activities DataFrame (should be filtered by date range if needed)
        
    Returns:
        Total distance in kilometers for the current week
    """
    if df.empty:
        return 0.0
    
    today = pd.Timestamp.now(tz=df["date"].dt.tz if df["date"].dt.tz is not None else None).normalize()
    
    # Get Monday of current week
    days_since_monday = today.weekday()
    week_start = today - pd.Timedelta(days=days_since_monday)
    week_end = week_start + pd.Timedelta(days=6)
    
    mask = (df["date"].dt.date >= week_start.date()) & (df["date"].dt.date <= week_end.date())
    return df.loc[mask, "distance_km"].sum()


def distance_this_month(df: pd.DataFrame) -> float:
    """
    Calculate total distance for the current month.
    
    Args:
        df: Normalized activities DataFrame
        
    Returns:
        Total distance in kilometers for the current month
    """
    if df.empty:
        return 0.0
    
    today = pd.Timestamp.now(tz=df["date"].dt.tz if df["date"].dt.tz is not None else None)
    
    # First day of current month
    month_start = today.replace(day=1).normalize()
    month_end = today.normalize()
    
    mask = (df["date"] >= month_start) & (df["date"] <= month_end)
    return df.loc[mask, "distance_km"].sum()


def distance_this_year(df: pd.DataFrame) -> float:
    """
    Calculate total distance for the current year (year-to-date).
    
    Args:
        df: Normalized activities DataFrame
        
    Returns:
        Total distance in kilometers for the current year
    """
    if df.empty:
        return 0.0
    
    today = pd.Timestamp.now(tz=df["date"].dt.tz if df["date"].dt.tz is not None else None)
    
    # First day of current year
    year_start = today.replace(month=1, day=1).normalize()
    year_end = today.normalize()
    
    mask = (df["date"] >= year_start) & (df["date"] <= year_end)
    return df.loc[mask, "distance_km"].sum()


def count_activities(df: pd.DataFrame) -> int:
    """
    Count total number of activities in the filtered DataFrame.
    
    Args:
        df: Normalized activities DataFrame (already filtered by user selections)
        
    Returns:
        Number of activities
    """
    return len(df)

