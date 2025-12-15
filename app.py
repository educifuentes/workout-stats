"""
Strava Training Dashboard - Single-page Streamlit application.

Displays volume and pace metrics from Strava activities with interactive charts and filters.
Uses dark theme and Altair for visualizations.
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta
from utils.strava_api import get_access_token, fetch_activities, fetch_athlete
from utils.transforms import normalize_activities
from utils.kpis import distance_this_week, distance_this_month, distance_this_year, count_activities

# Page configuration
st.set_page_config(
    page_title="Workout Dashboard",
    page_icon=":pool:",
    layout="wide",
    initial_sidebar_state="expanded"
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


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_athlete():
    """
    Load athlete profile information from Strava API.
    
    Returns:
        Dictionary with athlete data, None if fetch fails
    """
    try:
        secrets = st.secrets["strava"]
        client_id = secrets["client_id"]
        client_secret = secrets["client_secret"]
        refresh_token = secrets.get("refresh_token")
        access_token = secrets.get("access_token")
    except KeyError:
        return None
    
    if not refresh_token and not access_token:
        return None
    
    # Get access token
    access_token = get_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        access_token=access_token
    )
    
    if not access_token:
        return None
    
    # Fetch athlete profile
    athlete = fetch_athlete(access_token)
    return athlete


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
    
    # Date range filter - apply both start and end dates inclusively
    start_date, end_date = date_range
    if start_date and end_date:
        # Ensure date column is datetime for proper comparison
        date_series = pd.to_datetime(filtered["date"]).dt.date
        filtered = filtered[
            (date_series >= start_date) & 
            (date_series <= end_date)
        ]
    elif start_date:
        date_series = pd.to_datetime(filtered["date"]).dt.date
        filtered = filtered[date_series >= start_date]
    elif end_date:
        date_series = pd.to_datetime(filtered["date"]).dt.date
        filtered = filtered[date_series <= end_date]
    
    # Sport type filter
    if sport_type != "All":
        filtered = filtered[filtered["sport_type"] == sport_type]
    
    return filtered


def main():
    """Main application entry point."""
    
    # Header section
    st.title(":material/pool: Workout Dashboard")
    st.markdown("""
    Track your training volume and pace metrics from Strava activities.
    This dashboard shows distance trends over time and pace analysis by workout.
    """)
    
    # Load athlete profile information
    athlete = load_athlete()
    if athlete:
        athlete_name = athlete.get("firstname", "") + " " + athlete.get("lastname", "")
        athlete_name = athlete_name.strip() if athlete_name.strip() else athlete.get("username", "Athlete")
        
        # Calculate age from date of birth if available
        dob = athlete.get("dateofbirth")
        age = None
        if dob:
            try:
                birth_date = datetime.strptime(dob, "%Y-%m-%d").date()
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            except:
                pass
        
        # Display athlete profile
        profile_text = f"Athlete: **{athlete_name}**"
        if age is not None:
            profile_text += f" • Age: {age}"
        
        st.markdown(profile_text)
    
    # Load raw activities (cached)
    raw_activities = load_activities()
    
    if raw_activities.empty:
        st.stop()
    
    # Normalize activities
    activities_df = normalize_activities(raw_activities)
    
    if activities_df.empty:
        st.warning("No activities after normalization. Check date filters.")
        st.stop()
    
    # Global controls section - moved to sidebar
    with st.sidebar:
        st.header("Controls")
        
        if st.button("🔄 Refresh Data from Strava", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        
        # Date range selectors - separate inputs
        min_date = activities_df["date"].dt.date.min()
        max_date = activities_df["date"].dt.date.max()
        
        start_date = st.date_input(
            "Start Date",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            help="Select the start date for analysis"
        )
        
        end_date = st.date_input(
            "End Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            help="Select the end date for analysis"
        )
        
        # Ensure start_date <= end_date
        if start_date > end_date:
            st.warning("Start date must be before or equal to end date. Adjusting start date.")
            start_date = end_date
        
        date_range = (start_date, end_date)
        
        sport_types = ["All"] + sorted(activities_df["sport_type"].unique().tolist())
        selected_sport = st.selectbox(
            "Sport Type",
            options=sport_types,
            index=0,
            help="Filter activities by sport type"
        )
        
        st.divider()
        
        # Volume granularity control
        granularity = st.selectbox(
            "Volume Granularity",
            options=["Day", "Week", "Month"],
            index=0,
            key="volume_granularity"
        )
        
        st.divider()
    
    # Apply filters
    filtered_df = filter_dataframe(activities_df, date_range, selected_sport)
    
    if filtered_df.empty:
        st.warning("No activities match the selected filters.")
        st.stop()
    
    # KPIs section
    st.divider()
    st.subheader("Stats")
    
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
        st.metric("Total Workouts", f"{activity_count}")
    
    # Volume section
    st.divider()
    st.subheader("Training Volume")
    
    # Aggregate by selected period using pandas date truncation
    if not filtered_df.empty:
        # Map granularity to pandas frequency
        freq_map = {
            "Day": "D",
            "Week": "W",
            "Month": "M"
        }
        freq = freq_map[granularity]
        
        # Ensure date column is timezone-naive datetime
        df_for_agg = filtered_df.copy()
        df_for_agg['date'] = pd.to_datetime(df_for_agg['date']).dt.tz_localize(None).dt.normalize()
        
        # Aggregate using pd.Grouper (equivalent to SQL DATE_TRUNC)
        aggregated = df_for_agg.groupby(pd.Grouper(key='date', freq=freq)).agg({
            'distance_km': 'sum',
            'sport_type': 'count'
        }).reset_index()
        aggregated.columns = ['date', 'total_distance_km', 'activity_count']
        
        # Remove rows with no activities (only show actual data)
        aggregated = aggregated[aggregated['activity_count'] > 0].copy()
        
        if not aggregated.empty:
            # Sort by date
            aggregated = aggregated.sort_values('date')
            
            # Convert distance to meters for y-axis
            aggregated['total_distance_m'] = aggregated['total_distance_km'] * 1000
            
            # Create bar chart with light blue color
            light_blue = "#60a5fa"  # Tailwind blue-400
            
            chart = (
                alt.Chart(aggregated)
                .mark_bar(color=light_blue)
                .encode(
                    x=alt.X(
                        'date:T',
                        title=None,
                        axis=alt.Axis(
                            format='%Y-%m-%d',
                            labelAngle=-45,
                            labelFontSize=9
                        )
                    ),
                    y=alt.Y('total_distance_m:Q', title=None),
                    tooltip=[
                        alt.Tooltip('date:T', format='%Y-%m-%d'),
                        alt.Tooltip('total_distance_m:Q', format='.0f', title='Distance (m)'),
                        alt.Tooltip('activity_count:Q', format='.0f', title='Activities')
                    ]
                )
                .properties(
                    width=600,
                    height=300
                )
            )
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No data available for the selected granularity.")
    
    # Data table section
    st.divider()
    st.subheader("Activity Data")
    
    # Prepare table data
    table_df = filtered_df.copy()
    
    # Calculate pace in seconds per 100 meters
    if "pace_s_per_100m" in table_df.columns:
        pace_col = "pace_s_per_100m"
    elif "pace_s_per_km" in table_df.columns:
        # Calculate from seconds per km: divide by 10
        table_df["pace_s_per_100m"] = table_df["pace_s_per_km"] / 10.0
        pace_col = "pace_s_per_100m"
    elif "pace_min_per_km" in table_df.columns:
        # Calculate from minutes per km: convert to seconds per km, then divide by 10
        table_df["pace_s_per_100m"] = (table_df["pace_min_per_km"] * 60) / 10.0
        pace_col = "pace_s_per_100m"
    else:
        pace_col = None
    
    # Format columns for display
    display_columns = {
        "date": "Date",
        "sport_type": "Sport",
        "name": "Activity Name",
        "distance_km": "Distance (km)",
        "moving_time": "Moving Time (s)",
    }
    
    if pace_col:
        display_columns[pace_col] = "Pace (s/100m)"
    
    # Select and rename columns
    available_cols = [col for col in display_columns.keys() if col in table_df.columns]
    table_display = table_df[available_cols].copy()
    table_display = table_display.rename(columns=display_columns)
    
    # Format date
    if "Date" in table_display.columns:
        table_display["Date"] = table_display["Date"].dt.strftime("%Y-%m-%d %H:%M")
    
    # Format pace as seconds per 100m (simple number format)
    if "Pace (s/100m)" in table_display.columns:
        table_display["Pace (s/100m)"] = table_display["Pace (s/100m)"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) and x > 0 else "N/A"
        )
    
    # Format distance
    if "Distance (km)" in table_display.columns:
        table_display["Distance (km)"] = table_display["Distance (km)"].apply(lambda x: f"{x:.2f}")
    
    # Display table
    st.table(table_display)
    
    # Download button
    csv = table_display.to_csv(index=False)
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=f"strava_activities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


if __name__ == "__main__":
    main()

