# Collector Deployment

See the workspace-level `DEPLOYMENT_GUIDE.md` for the full GitHub, R2, Neon, and Vercel flow.

Short version:

1. Push this folder to public repo `collective-watchdog-data-collector`.
2. Add R2 secrets in GitHub:
   - `R2_BUCKET`
   - `R2_ENDPOINT_URL`
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
3. Run the `Collect Polymarket Data` workflow manually.
4. Confirm R2 contains `latest/dashboard.json`.

