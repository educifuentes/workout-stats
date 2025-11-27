"""
Data transformation and normalization module.

Processes raw Strava activity data into normalized, analysis-ready format.
Computes pace, distance buckets, and aggregation keys for time-based analysis.
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Optional


def normalize_activities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize raw Strava activities DataFrame into analysis-ready format.
    
    Expected input fields from Strava API:
    - start_date_local: ISO 8601 datetime string
    - distance: meters (float)
    - moving_time: seconds (int)
    - elapsed_time: seconds (int, optional)
    - average_speed: meters per second (float)
    - sport_type: string (e.g., "Run", "Ride")
    - name: activity name (string)
    
    Returns DataFrame with normalized columns:
    - date: date component (timezone-aware if possible)
    - distance_km: distance in kilometers
    - moving_time: moving time in seconds (preserved)
    - pace_s_per_km: pace in seconds per kilometer (for running)
    - pace_min_per_km: pace in minutes per kilometer (for running)
    - year, year_week, year_month: aggregation keys
    - distance_bucket: categorical distance ranges
    - sport_type, name: preserved from original
    
    Assumptions:
    - Uses start_date_local for timezone-aware date handling
    - Limits to last 2 years of activities by default
    - Pace calculation only meaningful for running activities
    """
    if df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    
    # Parse start_date_local to datetime
    if "start_date_local" in df.columns:
        df["date"] = pd.to_datetime(df["start_date_local"])
    elif "start_date" in df.columns:
        df["date"] = pd.to_datetime(df["start_date"])
    else:
        raise ValueError("No date column found in activities data")
    
    # Filter to last 2 years (configurable history window)
    cutoff_date = pd.Timestamp.now(tz=df["date"].dt.tz) - pd.Timedelta(days=730)
    df = df[df["date"] >= cutoff_date].copy()
    
    # Convert distance from meters to kilometers
    df["distance_km"] = df["distance"] / 1000.0
    
    # Compute pace (seconds per km and minutes per km)
    # Only valid when distance > 0
    mask_valid_distance = df["distance_km"] > 0
    
    df["pace_s_per_km"] = None
    df["pace_min_per_km"] = None
    
    # Pace = time / distance
    df.loc[mask_valid_distance, "pace_s_per_km"] = (
        df.loc[mask_valid_distance, "moving_time"] / 
        df.loc[mask_valid_distance, "distance_km"]
    )
    
    df.loc[mask_valid_distance, "pace_min_per_km"] = (
        df.loc[mask_valid_distance, "pace_s_per_km"] / 60.0
    )
    
    # Create aggregation keys
    df["year"] = df["date"].dt.year
    df["year_week"] = df["date"].dt.to_period("W").astype(str)
    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    
    # Create distance buckets (useful for analysis)
    def get_distance_bucket(distance_km: float, sport_type: str) -> str:
        """Categorize activity by distance range."""
        if pd.isna(distance_km) or distance_km == 0:
            return "Unknown"
        
        if sport_type == "Run":
            if distance_km < 5:
                return "<5K"
            elif distance_km < 10:
                return "5-10K"
            elif distance_km < 21.1:
                return "10K-Half"
            elif distance_km < 42.2:
                return "Half-Full"
            else:
                return ">Marathon"
        elif sport_type == "Ride":
            if distance_km < 20:
                return "<20K"
            elif distance_km < 50:
                return "20-50K"
            elif distance_km < 100:
                return "50-100K"
            else:
                return ">100K"
        else:
            # Generic buckets for other sports
            if distance_km < 5:
                return "<5K"
            elif distance_km < 10:
                return "5-10K"
            else:
                return ">10K"
    
    df["distance_bucket"] = df.apply(
        lambda row: get_distance_bucket(row["distance_km"], row.get("sport_type", "Unknown")),
        axis=1
    )
    
    # Select and order relevant columns for analysis
    columns_to_keep = [
        "date",
        "sport_type",
        "name",
        "distance_km",
        "moving_time",
        "elapsed_time",
        "pace_s_per_km",
        "pace_min_per_km",
        "average_speed",
        "year",
        "year_week",
        "year_month",
        "distance_bucket"
    ]
    
    # Keep only columns that exist
    available_columns = [col for col in columns_to_keep if col in df.columns]
    df_normalized = df[available_columns].copy()
    
    return df_normalized


def aggregate_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    Aggregate activities by time period (week, month, or year).
    
    Args:
        df: Normalized activities DataFrame
        period: One of "week", "month", or "year"
        
    Returns:
        DataFrame aggregated by the specified period with:
        - period key (year_week, year_month, or year)
        - total_distance_km: sum of distance
        - activity_count: number of activities
        - avg_pace_min_per_km: average pace (for running activities only)
    """
    if df.empty:
        return pd.DataFrame()
    
    period_key_map = {
        "week": "year_week",
        "month": "year_month",
        "year": "year"
    }
    
    if period not in period_key_map:
        raise ValueError(f"Period must be one of {list(period_key_map.keys())}")
    
    period_key = period_key_map[period]
    
    # Aggregate distance and count
    aggregated = df.groupby(period_key).agg({
        "distance_km": "sum",
        "sport_type": "count"
    }).reset_index()
    aggregated.columns = [period_key, "total_distance_km", "activity_count"]
    
    # Compute average pace for running activities only (if pace data exists)
    if "pace_min_per_km" in df.columns:
        running_df = df[df["sport_type"] == "Run"].copy()
        if not running_df.empty and running_df["pace_min_per_km"].notna().any():
            pace_agg = running_df.groupby(period_key)["pace_min_per_km"].mean().reset_index()
            pace_agg.columns = [period_key, "avg_pace_min_per_km"]
            aggregated = aggregated.merge(pace_agg, on=period_key, how="left")
    
    # Sort by period (most recent first for week/month, oldest first for year)
    if period == "year":
        aggregated = aggregated.sort_values(period_key)
    else:
        aggregated = aggregated.sort_values(period_key, ascending=False)
    
    return aggregated

