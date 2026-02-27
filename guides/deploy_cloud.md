# Deploying to Google Cloud

This project includes scripts to automate the deployment process to Google Cloud Run.

## Key Services Used

To deploy this application, you will use **both** Cloud Build and Cloud Run:

1.  **Cloud Build**: This service builds your application code into a Docker container image. It runs the build steps defined in the `Dockerfile` (or automatically detects languages).
    - _Usage_: The `scripts/deploy.sh` script runs `gcloud builds submit` to bundle your code and save the image to Artifact Registry.
2.  **Cloud Run**: This service takes the Docker image built by Cloud Build and runs it as a scalable web service.
    - _Usage_: The `scripts/deploy.sh` script runs `gcloud run deploy` to launch the container in a managed serverless environment.

## Prerequisites

1.  **GCP Credentials**: Ensure you have set up your GCP project and credentials. See [GCP Credentials Guide](gcp_credentials.md) for details.
2.  **Enabled APIs**: You must enable both the **Cloud Build API** and **Cloud Run API** (along with Artifact Registry and Secret Manager). The [GCP Credentials Guide](gcp_credentials.md) covers this.
3.  **gcloud CLI**: Make sure you have the `gcloud` CLI installed and authenticated.

## Deployment Steps

The deployment process is automated via the `scripts/deploy.sh` script.

### 1. Upload Secrets

Before deploying, ensure your local secrets in `.streamlit/secrets.toml` are uploaded to Google Secret Manager. The deployment script handles this calling `scripts/upload_secrets.sh`, but you can also run it manually:

```bash
./scripts/upload_secrets.sh
```

### 2. Run Deployment Script

Run the main deployment script:

```bash
./scripts/deploy.sh
```

This script will:

1.  Upload/Update secrets in Secret Manager.
2.  Grant necessary permissions to the Cloud Run service account to access secrets.
3.  Ensure the Artifact Registry repository exists.
4.  Build the Docker image using Cloud Build.
5.  Deploy the service to Cloud Run.

## Configuration

The deployment configuration variables are located at the top of `scripts/deploy.sh`:

- `SERVICE_NAME`: The name of the Cloud Run service (default: `time-track-dashboard`).
- `REGION`: The GCP region (default: `southamerica-west1`).

### 3. Continuous Deployment (CD) with GitHub Tags

You can automate deployments so that pushing a specific tag (e.g., `v1.0.0`) to your GitHub repository automatically triggers a build and deploy to Cloud Run using the `cloudbuild.yaml` configuration in this repository.

#### Step A: Connect your Repository

1. Open the [Google Cloud Console - Cloud Build Repositories](https://console.cloud.google.com/cloud-build/repositories).
2. Click **Connect Repository**.
3. Select **GitHub** and authenticate your GitHub account.
4. Select the repository containing your `time-track-dashboard` code.

#### Step B: Create a Tag-Based Trigger

The easiest way to configure this with the modern Cloud Build integration (2nd gen) is via the UI:

1. Go to **Cloud Build > Triggers** in the Google Cloud Console.
2. Click **Create Trigger**.
3. **Name**: `time-track-dashboard-tag-deploy`
4. **Event**: Select "Push new tag".
5. **Source**: Select your connected repository (e.g., `time-track-dashboard`).
6. **Tag**: Regex `^v.*$` (matches any tag starting with "v").
7. **Configuration**: "Cloud Build configuration file (yaml or json)".
8. **Location**: `cloudbuild.yaml`
9. Click **Create**.

_Note: If you prefer the CLI, the 2nd generation repository syntax requires the exact connection string rather than the repo owner/name:_

```bash
# You must adjust the specific projects/locations/connections/repositories string!
gcloud builds triggers create github \
    --name="time-track-dashboard-tag-deploy" \
    --repository="projects/YOUR_PROJECT_ID/locations/southamerica-west1/connections/YOUR_CONNECTION/repositories/time-track-dashboard" \
    --tag-pattern="^v.*$" \
    --build-config="cloudbuild.yaml" \
    --region="southamerica-west1"
```

#### Step C: Grant Cloud Build Permissions

The default Cloud Build service account needs permission to deploy to Cloud Run, act as the Cloud Run service account, and access your secrets. Run these commands:

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 1. Allow Cloud Build to act as the Cloud Run Service Account
gcloud iam service-accounts add-iam-policy-binding $COMPUTE_SA \
    --member="serviceAccount:$BUILD_SA" \
    --role="roles/iam.serviceAccountUser"

# 2. Allow Cloud Build to deploy to Cloud Run
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$BUILD_SA" \
    --role="roles/run.developer"

# 3. Allow Cloud Build to upload artifacts (if not already granted)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$BUILD_SA" \
    --role="roles/artifactregistry.writer"
```

#### Step D: Push a Tag to Deploy

When you are ready to release a new version, simply commit your code, tag it, and push the tag to GitHub:

```bash
git add .
git commit -m "Your release message"
git push origin main
git tag v1.0.0
git push origin v1.0.0
```

Cloud Build will automatically intercept the `v1.0.0` tag, use `cloudbuild.yaml` to build the Docker image, append the tag to the image, and deploy it to Cloud Run.

#### Secret Management for CD

Since `.streamlit/secrets.toml` is **not** in your repository, updating secrets requires a manual step.

- Run the provided script to upload your local secrets and configure the running service to use them:
  ```bash
  ./scripts/update_cloud_run_secrets.sh
  ```
- This script uploads the current state of your local `.streamlit/secrets.toml` to Secret Manager and updates the Cloud Run service to mount it.
