# Release Process (CalVer)

This project uses [Calendar Versioning (CalVer)](https://calver.org/) to track releases. The format we use is `YY.MM.DD`.

Whenever a new git tag is pushed to the repository in this format (prefixed with a `v`), Google Cloud Build will automatically trigger a deployment to Cloud Run.

## Steps to Release a New Version

1. **Ensure all changes are committed on `main`**

   ```bash
   git add .
   git commit -m "Your descriptive commit message"
   git push origin main
   ```

2. **Generate the CalVer Tag**
   Determine today's date in `YY.MM.DD` format.
   - _Example: For February 20th, 2026, the version is `26.02.20`_
   - _The tag must start with a lowercase `v`_

3. **Tag the commit**

   ```bash
   git tag v26.02.20
   ```

4. **Push the tag to GitHub**
   ```bash
   git push origin v26.02.20
   ```

## What Happens Next?

Once the tag is pushed, you can view the build progress in the [Google Cloud Console -> Cloud Build -> History](https://console.cloud.google.com/cloud-build/builds). Upon successful build, the new version will be live on Cloud Run.
