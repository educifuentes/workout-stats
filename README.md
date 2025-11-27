# Strava Training Dashboard

A single-page Streamlit application that displays training volume and pace metrics from your Strava account.

## Features

- **KPIs**: Weekly, monthly, and yearly distance totals
- **Volume Charts**: Distance trends over time (by week, month, or year)
- **Pace Analysis**: Time-series pace visualization and distance vs pace scatter plots
- **Activity Table**: Detailed view of all activities with filtering
- **Dark Theme**: Modern, minimal dark UI optimized for data visualization

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Strava API Credentials

#### Option A: Using the Helper Script (Recommended)

The easiest way to get a refresh token with the correct scopes is to use the helper script:

```bash
python get_strava_token.py
```

This script will:
1. Guide you through the OAuth authorization flow
2. Generate the correct authorization URL with `activity:read_all` scope
3. Help you exchange the authorization code for tokens
4. Optionally update your `secrets.toml` file automatically

#### Option B: Manual Setup

1. Create a Strava application at https://www.strava.com/settings/api
2. Note your Client ID and Client Secret
3. **IMPORTANT**: Set authorization callback domain (e.g., `http://localhost` for local development)
4. Generate authorization URL with correct scopes:

```python
from urllib.parse import urlencode

params = {
    "client_id": "YOUR_CLIENT_ID",
    "response_type": "code",
    "redirect_uri": "http://localhost",  # Must match your app's redirect URI
    "approval_prompt": "auto",
    "scope": "read,activity:read_all"  # ⚠️ CRITICAL: Must include activity:read_all
}

auth_url = "https://www.strava.com/oauth/authorize?" + urlencode(params)
print(auth_url)  # Open this in your browser
```

5. After authorization, Strava redirects to your callback URL with a `code` parameter
6. Exchange the code for tokens using the OAuth token endpoint
7. Save the `refresh_token` (it's long-lived and used to get new access tokens)
8. Add credentials to `.streamlit/secrets.toml`:

```toml
[strava]
client_id = "your_client_id"
client_secret = "your_client_secret"
refresh_token = "your_refresh_token"
```

**⚠️ Important Notes:**
- Your refresh token **MUST** have `activity:read_all` scope to fetch activities
- Tokens created without this scope will fail with "access_token.activity:read_permission: missing" error
- The helper script (`get_strava_token.py`) ensures the correct scope is requested

### 3. Run the App

```bash
streamlit run app.py
```

## Project Structure

```
strava-stats/
├── app.py                  # Main Streamlit application
├── utils/
│   ├── strava_api.py      # Strava API client (OAuth + activity fetch)
│   ├── transforms.py      # Data normalization and aggregations
│   └── kpis.py            # KPI calculation functions
├── .streamlit/
│   ├── config.toml        # Dark theme configuration
│   └── secrets.toml       # Strava API credentials (not in git)
├── get_strava_token.py    # Helper script to get refresh token with correct scopes
├── test_strava_api.py     # Test script to verify API credentials
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Data Model

The app processes Strava activities and normalizes them into:

- **Date**: Timezone-aware date from `start_date_local`
- **Distance**: Converted from meters to kilometers
- **Pace**: Calculated as seconds/minutes per kilometer (for running activities)
- **Aggregation Keys**: Year, week, and month for time-based analysis
- **Distance Buckets**: Categorical ranges (e.g., <5K, 5-10K, etc.)

## Assumptions

- **History Window**: Last 2 years of activities (configurable in `transforms.py`)
- **Timezone**: Uses `start_date_local` from Strava API
- **Units**: 
  - Distance: kilometers
  - Pace: seconds or minutes per kilometer
  - Time: seconds (moving time)
- **Default Sport**: Running activities are the primary focus, but other sports can be filtered

## Troubleshooting

### "access_token.activity:read_permission: missing" Error

This error means your refresh token doesn't have the `activity:read_all` scope. To fix:

1. **Use the helper script** to get a new refresh token with correct scopes:
   ```bash
   python get_strava_token.py
   ```

2. **Or manually re-authorize** with the correct scope in the authorization URL:
   ```
   scope=read,activity:read_all
   ```

### Test Your Credentials

Run the test script to verify your API credentials work:

```bash
python test_strava_api.py
```

This will validate your tokens and test fetching activities.

## Notes

- Data is cached for 1 hour to reduce API calls
- Use the "Refresh Data" button to force a new API fetch
- The app fetches up to 5 pages (1000 activities) by default
- Pace calculations are only meaningful for activities with distance > 0
- Refresh tokens with incorrect scopes must be re-issued through OAuth

