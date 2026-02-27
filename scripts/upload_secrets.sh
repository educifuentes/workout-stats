#!/bin/bash

# Configuration
SECRET_NAME="spendee-dashboard-secrets"
PROJECT_ID=$(gcloud config get-value project)
SECRETS_FILE=".streamlit/secrets.toml"

if [ ! -f "$SECRETS_FILE" ]; then
    echo "Error: $SECRETS_FILE not found."
    exit 1
fi

echo "Checking if secret $SECRET_NAME exists..."
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "Secret exists. Adding new version..."
else
    echo "Creating new secret $SECRET_NAME..."
    gcloud secrets create "$SECRET_NAME" --replication-policy="automatic" --project="$PROJECT_ID"
fi

echo "Uploading contents of $SECRETS_FILE to $SECRET_NAME..."
gcloud secrets versions add "$SECRET_NAME" --data-file="$SECRETS_FILE" --project="$PROJECT_ID"

echo "Done! You can now reference this secret in your Cloud Run configuration."
echo "Secret URI: projects/$PROJECT_ID/secrets/$SECRET_NAME"
