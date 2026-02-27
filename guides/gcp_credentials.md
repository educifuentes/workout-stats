# Google Cloud Platform (GCP) Credentials Guide

This guide explains how to set up the necessary credentials for deploying the `time-track-dashboard` application to Google Cloud Run.

## Prerequisites

- A Google Cloud Platform account.
- `gcloud` CLI installed and configured.

## Steps

### 1. Create a Google Cloud Project

If you haven't already, create a new project in the Google Cloud Console.

```bash
# Create a new project (replace [PROJECT_ID] with your desired ID)
gcloud projects create [PROJECT_ID] --name="Spendee Expenses Dashboard"

# Set the project as the default for gcloud
gcloud config set project [PROJECT_ID]
```

### 2. Enable Required APIs

Enable the necessary APIs for the project:

```bash
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com
```

### 3. Create a Service Account (Optional but Recommended)

It's best practice to use a Service Account for deployment or specific application permissions.

```bash
# Create a service account
gcloud iam service-accounts create time-track-deployer \
    --display-name="Spendee Expenses Deployer"
```

### 4. Create and Download Service Account Key

To use the service account from your local machine (e.g., for uploading secrets or running scripts locally), you need a JSON key file.

> [!WARNING]
> **Security Warning**: Never commit your JSON key file to version control. Ensure `.secrets/` is in your `.gitignore` file.

1.  Create the `.secrets` directory if it doesn't exist:

    ```bash
    mkdir -p .secrets
    ```

2.  Generate and download the key:
    ```bash
    gcloud iam service-accounts keys create .secrets/gcp-key.json \
        --iam-account=time-track-deployer@$(gcloud config get-value project).iam.gserviceaccount.com
    ```

### 5. Configure gcloud to use the key (Optional)

If you need to execute commands as this service account:

```bash
gcloud auth activate-service-account --key-file=.secrets/gcp-key.json
```

### 6. Grant Necessary Permissions

Grant the service account permissions to deploy to Cloud Run, push to Artifact Registry, and access Secrets.

```bash
PROJECT_ID=$(gcloud config get-value project)
SA_EMAIL="time-track-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant verify deploy permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.admin" # For Cloud Build

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"
```

## Setup for Application

Ensure your `.streamlit/secrets.toml` file exists and is populated with your application secrets (e.g., database credentials, Google Sheets info). This file will be securely uploaded to Secret Manager using `scripts/upload_secrets.sh`.
