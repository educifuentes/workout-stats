"""
Strava API client module.

Handles OAuth token refresh and activity fetching from Strava Web API v3.
Uses refresh token flow to obtain short-lived access tokens.
"""

import requests
import pandas as pd
from typing import Optional
import streamlit as st


def get_access_token(client_id: str, client_secret: str, refresh_token: str = None, access_token: str = None) -> Optional[str]:
    """
    Get access token for Strava API.
    
    If access_token is provided, validates it first, then uses it if valid.
    Otherwise, exchanges refresh_token for a new access token using Strava OAuth endpoint.
    
    Args:
        client_id: Strava application client ID
        client_secret: Strava application client secret
        refresh_token: Strava refresh token (long-lived, optional if access_token provided)
        access_token: Optional direct access token (if provided, will validate it first)
        
    Returns:
        Access token string if successful, None otherwise
    """
    # If access_token is provided, validate it first
    if access_token:
        if validate_access_token(access_token):
            return access_token
        # If validation fails, try refresh if we have refresh_token
        if not refresh_token:
            st.warning("Provided access token is invalid and no refresh token available.")
            return None
    
    # Exchange refresh token for new access token
    if not refresh_token:
        st.error("No access token or refresh token provided.")
        return None
    
    url = "https://www.strava.com/oauth/token"
    
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        
        # Handle error responses with detailed messages
        if not response.ok:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("message", response.text or "Unknown error")
            st.error(f"Error refreshing access token: {error_msg}")
            if error_data.get("errors"):
                for err in error_data["errors"]:
                    st.error(f"  - {err.get('field', '')}: {err.get('code', '')} - {err.get('message', '')}")
            return None
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            st.error("No access token in response from Strava.")
            return None
            
        return access_token
        
    except requests.exceptions.RequestException as e:
        st.error(f"Network error refreshing access token: {e}")
        return None


def validate_access_token(access_token: str) -> bool:
    """
    Validate an access token by making a simple API call.
    
    Args:
        access_token: Access token to validate
        
    Returns:
        True if token is valid, False otherwise
    """
    url = "https://www.strava.com/api/v3/athlete"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.ok
    except requests.exceptions.RequestException:
        return False


def fetch_activities(access_token: str, per_page: int = 200, max_pages: int = 5) -> pd.DataFrame:
    """
    Fetch athlete activities from Strava API with pagination.
    
    Uses Strava's pagination (page parameter) to fetch multiple pages of activities.
    Limits to max_pages to avoid excessive API calls.
    
    Args:
        access_token: Valid Strava access token
        per_page: Number of activities per page (max 200)
        max_pages: Maximum number of pages to fetch
        
    Returns:
        DataFrame with activities data, empty DataFrame if fetch fails
    """
    url = "https://www.strava.com/api/v3/athlete/activities"
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    all_activities = []
    page = 1
    
    while page <= max_pages:
        params = {
            "per_page": per_page,
            "page": page
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # Check for HTTP errors and handle them with detailed messages
            if not response.ok:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass
                
                error_msg = error_data.get("message", f"HTTP {response.status_code}")
                st.error(f"Error fetching activities (page {page}): {error_msg}")
                
                if error_data.get("errors"):
                    for err in error_data["errors"]:
                        resource = err.get("resource", "")
                        field = err.get("field", "")
                        code = err.get("code", "")
                        st.error(f"  - {resource}.{field}: {code}")
                
                break
            
            activities = response.json()
            
            # If empty response, we've reached the end
            if not activities:
                break
                
            all_activities.extend(activities)
            
            # If we got fewer than per_page results, we're done
            if len(activities) < per_page:
                break
                
            page += 1
            
        except requests.exceptions.RequestException as e:
            st.error(f"Network error fetching activities (page {page}): {e}")
            break
    
    if not all_activities:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(all_activities)
    
    return df

