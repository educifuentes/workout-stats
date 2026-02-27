#!/bin/bash

# Ensure .streamlit directory exists
mkdir -p .streamlit

# Create secrets.toml from environment variables
echo "# Generated at runtime" > .streamlit/secrets.toml

if [ -n "$SUPABASE_URL" ]; then
    echo "SUPABASE_URL = \"$SUPABASE_URL\"" >> .streamlit/secrets.toml
fi

if [ -n "$SUPABASE_KEY" ]; then
    echo "SUPABASE_KEY = \"$SUPABASE_KEY\"" >> .streamlit/secrets.toml
fi

if [ -n "$ALLOWED_EMAILS" ]; then
    # Convert comma-separated string to TOML list: e.g. "a,b" -> ["a", "b"]
    FORMATTED_EMAILS=$(echo "$ALLOWED_EMAILS" | sed 's/,/","/g' | sed 's/^/["/' | sed 's/$/"]/')
    echo "allowed_emails = $FORMATTED_EMAILS" >> .streamlit/secrets.toml
fi

echo "[auth]" >> .streamlit/secrets.toml
echo "redirect_uri = \"${AUTH__REDIRECT_URI}\"" >> .streamlit/secrets.toml
echo "cookie_secret = \"${AUTH__COOKIE_SECRET}\"" >> .streamlit/secrets.toml
echo "client_id = \"${AUTH__CLIENT_ID}\"" >> .streamlit/secrets.toml
echo "client_secret = \"${AUTH__CLIENT_SECRET}\"" >> .streamlit/secrets.toml
echo "server_metadata_url = \"${AUTH__SERVER_METADATA_URL}\"" >> .streamlit/secrets.toml

# Execute the application
exec streamlit run app.py --server.port="${PORT:-8080}" --server.address=0.0.0.0
