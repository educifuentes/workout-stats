"""
Strava Training Dashboard - Single-page Streamlit application.

Displays volume and pace metrics from Strava activities with interactive charts and filters.
Uses dark theme and Altair for visualizations.
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta
from utils.strava_api import get_access_token, fetch_activities
from utils.transforms import normalize_activities, aggregate_by_period
from utils.kpis import distance_this_week, distance_this_month, distance_this_year, count_activities

# Page configuration
st.set_page_config(
    page_title="Strava Training Dashboard",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed"
)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_activities():
    """
    Load activities from Strava API.
    
    This function:
    1. Reads Strava credentials from Streamlit secrets
    2. Obtains an access token via OAuth refresh
    3. Fetches activities with pagination
    4. Returns raw activities DataFrame
    
    Cached to avoid hitting API on every rerun (cleared via button or cache invalidation).
    """
    try:
        secrets = st.secrets["strava"]
        client_id = secrets["client_id"]
        client_secret = secrets["client_secret"]
        refresh_token = secrets.get("refresh_token")  # Optional if access_token provided
        access_token = secrets.get("access_token")  # Optional, can use directly
    except KeyError as e:
        st.error(f"Missing required Strava secret: {e}. Please configure secrets in .streamlit/secrets.toml")
        st.info("Required: client_id, client_secret. Optional: refresh_token OR access_token")
        return pd.DataFrame()
    
    # Validate that we have either refresh_token or access_token
    if not refresh_token and not access_token:
        st.error("Either 'refresh_token' or 'access_token' must be provided in secrets.")
        return pd.DataFrame()
    
    # Get access token (will use refresh_token to get new one, or validate existing access_token)
    access_token = get_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        access_token=access_token
    )
    
    if not access_token:
        st.error("Failed to obtain valid access token. Check your credentials.")
        st.info("Make sure your refresh_token is valid or provide a valid access_token in secrets.")
        return pd.DataFrame()
    
    # Fetch activities
    with st.spinner("Fetching activities from Strava..."):
        activities_df = fetch_activities(access_token, per_page=200, max_pages=5)
    
    if activities_df.empty:
        st.warning("No activities found. Make sure you have activities in your Strava account.")
        return pd.DataFrame()
    
    return activities_df


def filter_dataframe(df: pd.DataFrame, date_range: tuple[date, date], sport_type: str) -> pd.DataFrame:
    """
    Apply global filters to the activities DataFrame.
    
    Args:
        df: Normalized activities DataFrame
        date_range: Tuple of (start_date, end_date)
        sport_type: Filter by sport type ("Run", "Ride", or "All")
        
    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df
    
    filtered = df.copy()
    
    # Date range filter
    start_date, end_date = date_range
    if start_date:
        filtered = filtered[filtered["date"].dt.date >= start_date]
    if end_date:
        filtered = filtered[filtered["date"].dt.date <= end_date]
    
    # Sport type filter
    if sport_type != "All":
        filtered = filtered[filtered["sport_type"] == sport_type]
    
    return filtered


def main():
    """Main application entry point."""
    
    # Header section
    st.title("🏃 Strava Training Dashboard")
    st.markdown("""
    Track your training volume and pace metrics from Strava activities.
    This dashboard shows distance trends over time and pace analysis by workout.
    """)
    
    # Load raw activities (cached)
    raw_activities = load_activities()
    
    if raw_activities.empty:
        st.stop()
    
    # Normalize activities
    activities_df = normalize_activities(raw_activities)
    
    if activities_df.empty:
        st.warning("No activities after normalization. Check date filters.")
        st.stop()
    
    # Global controls section
    st.divider()
    st.subheader("Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Data from Strava", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        # Date range selector
        min_date = activities_df["date"].dt.date.min()
        max_date = activities_df["date"].dt.date.max()
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Select the date range for analysis"
        )
        
        # Handle date range input (can be single date or tuple)
        if isinstance(date_range, date):
            date_range = (date_range, max_date)
        elif isinstance(date_range, tuple) and len(date_range) == 2:
            # Ensure both dates are set
            if date_range[1] is None:
                date_range = (date_range[0] if date_range[0] else min_date, max_date)
            elif date_range[0] is None:
                date_range = (min_date, date_range[1])
        else:
            date_range = (min_date, max_date)
    
    with col3:
        sport_types = ["All"] + sorted(activities_df["sport_type"].unique().tolist())
        selected_sport = st.selectbox(
            "Sport Type",
            options=sport_types,
            index=0,
            help="Filter activities by sport type"
        )
    
    # Apply filters
    filtered_df = filter_dataframe(activities_df, date_range, selected_sport)
    
    if filtered_df.empty:
        st.warning("No activities match the selected filters.")
        st.stop()
    
    # KPIs section
    st.divider()
    st.subheader("Key Performance Indicators")
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        week_dist = distance_this_week(filtered_df)
        st.metric("Distance This Week", f"{week_dist:.1f} km")
    
    with kpi_col2:
        month_dist = distance_this_month(filtered_df)
        st.metric("Distance This Month", f"{month_dist:.1f} km")
    
    with kpi_col3:
        year_dist = distance_this_year(filtered_df)
        st.metric("Distance This Year (YTD)", f"{year_dist:.1f} km")
    
    with kpi_col4:
        activity_count = count_activities(filtered_df)
        st.metric("Total Activities", f"{activity_count}")
    
    # Volume section
    st.divider()
    st.subheader("Training Volume")
    
    vol_col1, vol_col2 = st.columns([1, 4])
    
    with vol_col1:
        granularity = st.selectbox(
            "Granularity",
            options=["Week", "Month", "Year"],
            index=0,
            key="volume_granularity"
        )
    
    # Aggregate by selected period
    period_map = {"Week": "week", "Month": "month", "Year": "year"}
    period_key = period_map[granularity]
    aggregated = aggregate_by_period(filtered_df, period_key)
    
    if not aggregated.empty:
        # Create volume chart (bar chart for week/month, line for year)
        chart_type = "bar" if granularity in ["Week", "Month"] else "bar"
        
        # Prepare data for chart
        chart_data = aggregated.copy()
        
        # Create Altair chart
        if chart_type == "bar":
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X(
                    f"{period_key}:O",
                    title=granularity,
                    sort=alt.SortField(field=f"{period_key}", order="ascending") if granularity == "Year" else None
                ),
                y=alt.Y(
                    "total_distance_km:Q",
                    title="Distance (km)"
                ),
                tooltip=[
                    alt.Tooltip(f"{period_key}:O", title=granularity),
                    alt.Tooltip("total_distance_km:Q", title="Distance (km)", format=".1f"),
                    alt.Tooltip("activity_count:Q", title="Activities")
                ]
            ).properties(
                width=700,
                height=400,
                title=f"Distance per {granularity}"
            ).configure(
                background="transparent",
                axis=alt.AxisConfig(labelColor="white", titleColor="white", gridColor="#333333"),
                text=alt.TextConfig(color="white")
            )
        else:
            chart = alt.Chart(chart_data).mark_line(point=True).encode(
                x=alt.X(
                    f"{period_key}:O",
                    title=granularity
                ),
                y=alt.Y(
                    "total_distance_km:Q",
                    title="Distance (km)"
                ),
                tooltip=[
                    alt.Tooltip(f"{period_key}:O", title=granularity),
                    alt.Tooltip("total_distance_km:Q", title="Distance (km)", format=".1f"),
                    alt.Tooltip("activity_count:Q", title="Activities")
                ]
            ).properties(
                width=700,
                height=400,
                title=f"Distance per {granularity}"
            ).configure(
                background="transparent",
                axis=alt.AxisConfig(labelColor="white", titleColor="white", gridColor="#333333"),
                text=alt.TextConfig(color="white")
            )
        
        with vol_col2:
            st.altair_chart(chart, use_container_width=True)
    
    # Pace section
    st.divider()
    st.subheader("Pace by Workout")
    
    pace_col1, pace_col2 = st.columns([1, 4])
    
    with pace_col1:
        pace_units = st.radio(
            "Display Units",
            options=["min/km", "s/km"],
            index=0,
            key="pace_units"
        )
        
        # Distance filter for pace analysis
        if "Run" in filtered_df["sport_type"].values:
            min_dist = float(filtered_df["distance_km"].min())
            max_dist = float(filtered_df["distance_km"].max())
            
            dist_range = st.slider(
                "Distance Range (km)",
                min_value=min_dist,
                max_value=max_dist,
                value=(min_dist, max_dist),
                key="pace_dist_filter"
            )
            
            # Filter by distance for pace charts
            pace_df = filtered_df[
                (filtered_df["distance_km"] >= dist_range[0]) &
                (filtered_df["distance_km"] <= dist_range[1])
            ].copy()
        else:
            pace_df = filtered_df.copy()
    
    # Pace time series chart
    if not pace_df.empty and "pace_min_per_km" in pace_df.columns:
        # Filter out activities without valid pace
        pace_df_valid = pace_df[pace_df["pace_min_per_km"].notna()].copy()
        
        if not pace_df_valid.empty:
            # Select y-axis value based on units
            if pace_units == "min/km":
                y_field = "pace_min_per_km"
                y_title = "Pace (min/km)"
            else:
                y_field = "pace_s_per_km"
                y_title = "Pace (s/km)"
            
            # Time series scatter/line chart
            time_series_chart = alt.Chart(pace_df_valid).mark_circle(size=60).encode(
                x=alt.X(
                    "date:T",
                    title="Date",
                    axis=alt.Axis(format="%Y-%m-%d")
                ),
                y=alt.Y(
                    f"{y_field}:Q",
                    title=y_title
                ),
                color=alt.Color(
                    "distance_bucket:N",
                    title="Distance Bucket",
                    scale=alt.Scale(scheme="category10")
                ),
                tooltip=[
                    alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                    alt.Tooltip("name:N", title="Activity"),
                    alt.Tooltip("distance_km:Q", title="Distance (km)", format=".2f"),
                    alt.Tooltip("pace_min_per_km:Q", title="Pace (min/km)", format=".2f"),
                    alt.Tooltip("sport_type:N", title="Sport")
                ]
            ).properties(
                width=700,
                height=400,
                title="Pace Over Time"
            ).configure(
                background="transparent",
                axis=alt.AxisConfig(labelColor="white", titleColor="white", gridColor="#333333"),
                legend=alt.LegendConfig(labelColor="white", titleColor="white"),
                text=alt.TextConfig(color="white")
            )
            
            with pace_col2:
                st.altair_chart(time_series_chart, use_container_width=True)
            
            # Distance vs Pace scatter chart
            st.markdown("#### Pace vs Distance")
            scatter_chart = alt.Chart(pace_df_valid).mark_circle(size=60).encode(
                x=alt.X(
                    "distance_km:Q",
                    title="Distance (km)"
                ),
                y=alt.Y(
                    f"{y_field}:Q",
                    title=y_title
                ),
                color=alt.Color(
                    "date:T",
                    title="Date",
                    scale=alt.Scale(scheme="viridis")
                ),
                tooltip=[
                    alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                    alt.Tooltip("name:N", title="Activity"),
                    alt.Tooltip("distance_km:Q", title="Distance (km)", format=".2f"),
                    alt.Tooltip("pace_min_per_km:Q", title="Pace (min/km)", format=".2f"),
                    alt.Tooltip("sport_type:N", title="Sport")
                ]
            ).properties(
                width=700,
                height=400
            ).configure(
                background="transparent",
                axis=alt.AxisConfig(labelColor="white", titleColor="white", gridColor="#333333"),
                legend=alt.LegendConfig(labelColor="white", titleColor="white"),
                text=alt.TextConfig(color="white")
            )
            
            st.altair_chart(scatter_chart, use_container_width=True)
        else:
            st.info("No activities with valid pace data in the selected filters.")
    else:
        st.info("Pace analysis is only available for activities with distance and time data.")
    
    # Data table section
    st.divider()
    st.subheader("Activity Table")
    
    # Prepare table data
    table_df = filtered_df.copy()
    
    # Format columns for display
    display_columns = {
        "date": "Date",
        "sport_type": "Sport",
        "name": "Activity Name",
        "distance_km": "Distance (km)",
        "moving_time": "Moving Time (s)",
        "pace_min_per_km": "Pace (min/km)"
    }
    
    # Select and rename columns
    available_cols = [col for col in display_columns.keys() if col in table_df.columns]
    table_display = table_df[available_cols].copy()
    table_display = table_display.rename(columns=display_columns)
    
    # Format date
    if "Date" in table_display.columns:
        table_display["Date"] = table_display["Date"].dt.strftime("%Y-%m-%d %H:%M")
    
    # Format pace
    if "Pace (min/km)" in table_display.columns:
        table_display["Pace (min/km)"] = table_display["Pace (min/km)"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
        )
    
    # Format distance
    if "Distance (km)" in table_display.columns:
        table_display["Distance (km)"] = table_display["Distance (km)"].apply(lambda x: f"{x:.2f}")
    
    st.dataframe(
        table_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )


if __name__ == "__main__":
    main()

