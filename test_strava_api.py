"""
Simple test script to verify Strava API credentials and fetch test data.

This script:
1. Reads credentials from .streamlit/secrets.toml
2. Gets/validates an access token
3. Tests fetching athlete info and activities
"""

import requests
import toml
import os
from pathlib import Path
from typing import Tuple, List


def load_secrets():
    """Load Strava credentials from secrets.toml file."""
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    
    if not secrets_path.exists():
        print(f"Error: Secrets file not found at {secrets_path}")
        return None
    
    try:
        with open(secrets_path, "r") as f:
            secrets = toml.load(f)
        return secrets.get("strava", {})
    except Exception as e:
        print(f"Error loading secrets: {e}")
        return None


def validate_access_token(access_token: str) -> Tuple[bool, List[str]]:
    """
    Validate an access token by fetching athlete info.
    
    Returns:
        Tuple of (is_valid, scopes_list)
    """
    url = "https://www.strava.com/api/v3/athlete"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.ok:
            athlete = response.json()
            print(f"✓ Access token is valid!")
            print(f"  Athlete: {athlete.get('firstname', '')} {athlete.get('lastname', '')}")
            print(f"  ID: {athlete.get('id', 'N/A')}")
            
            # Check scopes if available in response headers
            scopes_str = response.headers.get('X-RateLimit-Scope', '')
            scopes = [s.strip() for s in scopes_str.split(',')] if scopes_str else []
            
            return True, scopes
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            print(f"✗ Access token validation failed: {error_msg}")
            if error_data.get("errors"):
                for err in error_data["errors"]:
                    print(f"  - {err.get('resource', '')}.{err.get('field', '')}: {err.get('code', '')}")
            return False, []
    except Exception as e:
        print(f"✗ Error validating access token: {e}")
        return False, []


def get_access_token_from_refresh(client_id: str, client_secret: str, refresh_token: str):
    """Exchange refresh token for a new access token."""
    url = "https://www.strava.com/oauth/token"
    
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    try:
        print("Attempting to refresh access token...")
        response = requests.post(url, data=payload, timeout=10)
        
        if not response.ok:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            print(f"✗ Error refreshing token: {error_msg}")
            if error_data.get("errors"):
                for err in error_data["errors"]:
                    print(f"  - {err.get('field', '')}: {err.get('code', '')} - {err.get('message', '')}")
            return None
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if access_token:
            print("✓ Successfully obtained new access token")
            expires_at = token_data.get("expires_at")
            if expires_at:
                from datetime import datetime
                expires_dt = datetime.fromtimestamp(expires_at)
                print(f"  Expires at: {expires_dt}")
            return access_token
        else:
            print("✗ No access token in response")
            return None
            
    except Exception as e:
        print(f"✗ Network error refreshing token: {e}")
        return None


def fetch_test_activities(access_token: str, limit: int = 5):
    """Fetch a few activities to test the API."""
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"per_page": limit}
    
    try:
        print(f"\nFetching {limit} activities...")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if not response.ok:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            print(f"✗ Error fetching activities: {error_msg}")
            if error_data.get("errors"):
                for err in error_data["errors"]:
                    resource = err.get("resource", "")
                    field = err.get("field", "")
                    code = err.get("code", "")
                    print(f"  - {resource}.{field}: {code}")
                    
                    # Check for scope-related errors
                    if "read_permission" in code.lower() or "permission" in code.lower():
                        print("\n⚠️  SCOPE ERROR DETECTED!")
                        print("Your access token is missing the required 'activity:read_all' scope.")
                        print("\nTo fix this:")
                        print("1. Run: python get_strava_token.py")
                        print("2. Re-authorize with the correct scope")
                        print("3. Update your refresh_token in secrets.toml")
            return None
        
        activities = response.json()
        print(f"✓ Successfully fetched {len(activities)} activities\n")
        
        if activities:
            print("Sample activities:")
            for i, activity in enumerate(activities[:limit], 1):
                name = activity.get("name", "Unnamed")
                sport = activity.get("sport_type", "Unknown")
                distance = activity.get("distance", 0) / 1000  # Convert to km
                date = activity.get("start_date_local", "N/A")
                print(f"  {i}. {name}")
                print(f"     Sport: {sport}, Distance: {distance:.2f} km, Date: {date}")
        
        return activities
        
    except Exception as e:
        print(f"✗ Error fetching activities: {e}")
        return None


def main():
    """Main test function."""
    print("=" * 60)
    print("Strava API Test Script")
    print("=" * 60)
    
    # Load secrets
    print("\n1. Loading credentials from secrets.toml...")
    secrets = load_secrets()
    
    if not secrets:
        print("✗ Failed to load credentials. Exiting.")
        return
    
    client_id = secrets.get("client_id")
    client_secret = secrets.get("client_secret")
    refresh_token = secrets.get("refresh_token")
    access_token = secrets.get("access_token")
    
    if not client_id or not client_secret:
        print("✗ Missing required credentials: client_id or client_secret")
        return
    
    print("✓ Credentials loaded")
    print(f"  Client ID: {client_id}")
    print(f"  Has refresh_token: {bool(refresh_token)}")
    print(f"  Has access_token: {bool(access_token)}")
    
    # Get/validate access token
    print("\n2. Obtaining access token...")
    valid_token = None
    
    if access_token:
        print("  Found access_token in secrets, validating...")
        is_valid, scopes = validate_access_token(access_token)
        if is_valid:
            valid_token = access_token
            if scopes:
                print(f"  Scopes: {', '.join(scopes)}")
        else:
            print("  Access token invalid, trying refresh token...")
            access_token = None
    
    if not valid_token and refresh_token:
        valid_token = get_access_token_from_refresh(client_id, client_secret, refresh_token)
    
    if not valid_token:
        print("✗ Failed to obtain valid access token. Cannot proceed.")
        print("\nTroubleshooting tips:")
        print("  - Check if refresh_token is valid and not expired")
        print("  - Verify client_id and client_secret are correct")
        print("  - Ensure the token has 'activity:read_all' scope")
        return
    
    # Test fetching activities
    print("\n3. Testing activity fetch...")
    activities = fetch_test_activities(valid_token, limit=5)
    
    if activities:
        print("\n" + "=" * 60)
        print("✓ All tests passed! Your Strava API credentials are working.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ Activity fetch failed. Check the errors above.")
        print("=" * 60)


if __name__ == "__main__":
    main()

