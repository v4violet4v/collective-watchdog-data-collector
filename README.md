# collective-watchdog-data-collector

Public collector repo for `Collective Watchdog`.

This repo should contain only public-data ingestion and derived-data export logic. Do not commit API secrets, database URLs, R2 keys, or private website code.

## Purpose

- Fetch public Polymarket events, markets, tags, prices, trades, and whale-flow signals.
- Normalize data for research and dashboard display.
- Write structured rows to Neon.
- Export chart-ready JSON to Cloudflare R2.

## Planned Structure

```text
collector-public/
  src/
    collect_events.py
    collect_prices.py
    collect_trades.py
    compute_whales.py
    export_r2.py
  sql/
    schema.sql
  .github/workflows/
    collect.yml
  requirements.txt
```

## Data Policy

- Store public source IDs internally, but do not expose raw IDs in public JSON unless needed.
- Mask wallet addresses in public exports.
- Include `generated_at`, source name, and collector run metadata in exported JSON.
- Keep any user-specific wallet alert rules out of this public repo.

## Local Development

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python src/collect.py
```

The collector writes JSON into `dist/` by default. Configure R2 upload with:

- `R2_BUCKET`
- `R2_ENDPOINT_URL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `REQUIRE_R2_UPLOAD=true` in CI, so a workflow run fails if R2 secrets are missing or no JSON files are uploaded.

`R2_BUCKET` may be configured as either a GitHub secret or a GitHub repository variable.

If local Windows certificate verification fails during development, you can run a smoke test with `COLLECTOR_SSL_VERIFY=false`. Keep SSL verification enabled in GitHub Actions and production jobs.
