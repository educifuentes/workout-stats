"""
Helper script to generate Strava OAuth authorization URL and guide token setup.

This script helps you:
1. Generate the correct authorization URL with proper scopes
2. Guide you through the OAuth flow
3. Help exchange the authorization code for tokens
"""

import urllib.parse
import webbrowser
from pathlib import Path
import json


def load_client_credentials():
    """Load client_id and client_secret from secrets.toml."""
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    
    if not secrets_path.exists():
        print(f"Error: Secrets file not found at {secrets_path}")
        return None, None
    
    try:
        # Simple TOML parsing for just the strava section
        with open(secrets_path, "r") as f:
            content = f.read()
        
        # Extract client_id and client_secret
        client_id = None
        client_secret = None
        
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("client_id") and "=" in line:
                client_id = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("client_secret") and "=" in line:
                client_secret = line.split("=", 1)[1].strip().strip('"').strip("'")
        
        return client_id, client_secret
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None, None


def generate_authorization_url(client_id: str, redirect_uri: str = "http://localhost"):
    """
    Generate Strava OAuth authorization URL with correct scopes.
    
    Args:
        client_id: Your Strava application client ID
        redirect_uri: The redirect URI configured in your Strava app
        
    Returns:
        Authorization URL string
    """
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "auto",
        "scope": "read,activity:read_all"  # IMPORTANT: Includes activity:read_all scope
    }
    
    auth_url = "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(params)
    return auth_url


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str = "http://localhost"):
    """
    Exchange authorization code for access and refresh tokens.
    
    Args:
        client_id: Your Strava application client ID
        client_secret: Your Strava application client secret
        code: Authorization code from the redirect URL
        redirect_uri: The redirect URI used in authorization
        
    Returns:
        Dictionary with tokens or None if failed
    """
    url = "https://www.strava.com/oauth/token"
    
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code"
    }
    
    import requests
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        
        if not response.ok:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            print(f"✗ Error exchanging code for tokens: {error_msg}")
            if error_data.get("errors"):
                for err in error_data["errors"]:
                    print(f"  - {err.get('field', '')}: {err.get('code', '')}")
            return None
        
        token_data = response.json()
        return token_data
        
    except Exception as e:
        print(f"✗ Network error: {e}")
        return None


def main():
    """Main function to guide user through OAuth flow."""
    print("=" * 70)
    print("Strava OAuth Token Setup Helper")
    print("=" * 70)
    print("\nThis script helps you get a refresh token with the correct scopes.")
    print("You need 'activity:read_all' scope to fetch activities.\n")
    
    # Load client credentials
    print("1. Loading client credentials from secrets.toml...")
    client_id, client_secret = load_client_credentials()
    
    if not client_id or not client_secret:
        print("\n✗ Could not find client_id and/or client_secret in secrets.toml")
        print("\nPlease add them first:")
        print("  [strava]")
        print('  client_id = "YOUR_CLIENT_ID"')
        print('  client_secret = "YOUR_CLIENT_SECRET"')
        return
    
    print(f"✓ Found client_id: {client_id}")
    
    # Get redirect URI
    print("\n2. Configure redirect URI")
    print("   Make sure your Strava app has this redirect URI configured:")
    default_redirect = "http://localhost"
    redirect_uri = input(f"   Enter redirect URI (default: {default_redirect}): ").strip() or default_redirect
    print(f"   Using: {redirect_uri}\n")
    
    # Generate authorization URL
    print("3. Generating authorization URL with correct scopes...")
    auth_url = generate_authorization_url(client_id, redirect_uri)
    
    print("\n" + "=" * 70)
    print("STEP 1: Authorize your application")
    print("=" * 70)
    print("\nOpen this URL in your browser:")
    print(f"\n{auth_url}\n")
    
    # Offer to open in browser
    open_browser = input("Open URL in browser now? (y/n): ").strip().lower()
    if open_browser == 'y':
        webbrowser.open(auth_url)
    
    print("\nAfter authorizing, Strava will redirect you to:")
    print(f"  {redirect_uri}?code=AUTHORIZATION_CODE&scope=...")
    print("\nCopy the 'code' parameter from the URL.")
    
    # Get authorization code
    print("\n" + "=" * 70)
    print("STEP 2: Exchange code for tokens")
    print("=" * 70)
    auth_code = input("\nPaste the authorization code here: ").strip()
    
    if not auth_code:
        print("✗ No authorization code provided. Exiting.")
        return
    
    # Exchange code for tokens
    print("\nExchanging authorization code for tokens...")
    token_data = exchange_code_for_tokens(client_id, client_secret, auth_code, redirect_uri)
    
    if not token_data:
        print("\n✗ Failed to get tokens. Please try again.")
        return
    
    # Display tokens
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")
    
    print("\n" + "=" * 70)
    print("✓ SUCCESS! Tokens obtained")
    print("=" * 70)
    
    if expires_at:
        from datetime import datetime
        expires_dt = datetime.fromtimestamp(expires_at)
        print(f"\nAccess token expires at: {expires_dt}")
    
    scopes = token_data.get("scope", [])
    print(f"Scopes granted: {scopes if isinstance(scopes, str) else ', '.join(scopes)}")
    
    # Verify scope
    if isinstance(scopes, str):
        has_read_all = "activity:read_all" in scopes
    else:
        has_read_all = "activity:read_all" in scopes or any("activity:read_all" in str(s) for s in scopes)
    
    if not has_read_all:
        print("\n⚠ WARNING: Token does not have 'activity:read_all' scope!")
        print("You may need to re-authorize with the correct scope.")
    else:
        print("\n✓ Token has 'activity:read_all' scope - perfect!")
    
    # Update secrets file
    print("\n" + "=" * 70)
    print("STEP 3: Update secrets.toml")
    print("=" * 70)
    
    if refresh_token:
        secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
        print(f"\nUpdate your refresh_token in: {secrets_path}")
        print("\nAdd or update this line:")
        print(f'  refresh_token = "{refresh_token}"')
        
        update_file = input("\nUpdate secrets.toml file automatically? (y/n): ").strip().lower()
        
        if update_file == 'y':
            try:
                # Read existing file
                with open(secrets_path, "r") as f:
                    content = f.read()
                
                # Update refresh_token
                lines = content.split("\n")
                updated_lines = []
                refresh_updated = False
                
                for line in lines:
                    if line.strip().startswith("refresh_token"):
                        updated_lines.append(f'refresh_token = "{refresh_token}"')
                        refresh_updated = True
                    else:
                        updated_lines.append(line)
                
                if not refresh_updated:
                    # Add refresh_token if not present
                    if "[strava]" in content:
                        # Add after [strava] section
                        idx = content.find("[strava]")
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if line.strip() == "[strava]":
                                lines.insert(i + 1, f'refresh_token = "{refresh_token}"')
                                updated_lines = lines
                                refresh_updated = True
                                break
                
                if refresh_updated:
                    with open(secrets_path, "w") as f:
                        f.write("\n".join(updated_lines))
                    print(f"\n✓ Updated {secrets_path} with new refresh_token")
                else:
                    print("\n⚠ Could not automatically update file. Please update manually.")
                    
            except Exception as e:
                print(f"\n⚠ Error updating file: {e}")
                print("Please update manually.")
    
    print("\n" + "=" * 70)
    print("Setup complete! You can now use your refresh_token in the app.")
    print("=" * 70)


if __name__ == "__main__":
    main()

