#!/bin/sh

# Create the .streamlit directory if it doesn't exist
mkdir -p .streamlit

# Check if secrets.toml already exists (e.g. mounted via Secret Manager)
if [ -f ".streamlit/secrets.toml" ]; then
    echo "Using existing .streamlit/secrets.toml (likely mounted via Secret Manager)."
# Otherwise, check if the environment variable is set
elif [ -n "$STREAMLIT_SECRETS_CONTENTS" ]; then
    echo "Recreating secrets.toml from environment variable..."
    echo "$STREAMLIT_SECRETS_CONTENTS" > .streamlit/secrets.toml
else
    echo "No secrets found in .streamlit/secrets.toml or STREAMLIT_SECRETS_CONTENTS."
fi

# Start Streamlit
exec streamlit run app.py --server.port="${PORT:-8080}" --server.address=0.0.0.0
