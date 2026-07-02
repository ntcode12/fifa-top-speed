# FIFA Top Speed — Liquid Glass Redesign + Dagster Pipeline + S3

**Date:** 2026-07-02
**Status:** Approved

## Goal

Turn the one-shot scraper + Streamlit app into a proper data engineering
project: Terraform-provisioned S3 storage, an incremental Dagster pipeline
that backfills all available match reports (72 today, knockouts as they
publish), and a liquid-glass redesign of the Streamlit app with all bugs
fixed.

## Context

- Current data: `top_speeds.csv`, 1,512 rows from 48 matches scraped
  2026-06-24. The FIFA hub now lists 72 match-report PDFs (full group
  stage); knockout-round reports will appear through 2026-07-19.
- AWS account 032968994565, region us-east-1, credentials configured
  locally. Terraform will create real resources.
- App stays on Streamlit (deployed via Docker / HF Spaces).

## Architecture

```
FIFA hub ──> Dagster assets ──> s3://fifa-topspeed-<account>/
                │                   raw/pdfs/<match>.pdf
                │                   curated/top_speeds.parquet
                └──> data/top_speeds.csv (local fallback, committed)
Streamlit app ──reads──> S3 curated parquet, falls back to local CSV
```

### 1. Infrastructure — `infra/` (Terraform)

- One private S3 bucket: `fifa-topspeed-<account_id>` in us-east-1.
  - Prefixes: `raw/pdfs/` (immutable downloaded PDFs) and `curated/`
    (parsed parquet).
  - Versioning enabled, SSE-S3 encryption, public access fully blocked.
- Terraform state stays local (`infra/terraform.tfstate`, gitignored).
- Outputs: bucket name, consumed by the pipeline via env var
  `FIFA_BUCKET` (with a sensible default).

### 2. Pipeline — `pipeline/` (Dagster)

Dagster project with software-defined assets:

- `match_report_urls` — scrapes the hub page, returns the list of PDF
  URLs.
- `raw_match_pdfs` — downloads each PDF only if `raw/pdfs/<name>.pdf`
  is not already in S3 (incremental — knockout matches flow in
  automatically as FIFA publishes them).
- `top_speeds` — parses all raw PDFs (reading from S3), validates rows
  (speed within 15–40 km/h or null, non-empty player/team/match), writes
  `curated/top_speeds.parquet` to S3 and `data/top_speeds.csv` locally.
- A daily schedule; run ad hoc via `dagster dev` UI or
  `dagster asset materialize`.

Parsing logic (private-use-area font decode, physical-data page
extraction) moves from `main.py` into `pipeline/parsing.py` with unit
tests against a fixture PDF. `main.py` is retired.

### 3. App redesign — liquid glass (Streamlit)

- Deep dark gradient backdrop; frosted translucent cards
  (`backdrop-filter: blur`, soft 1px translucent borders, subtle inner
  glow) for KPI tiles, sections, and sidebar.
- Plotly charts re-themed for dark: transparent paper/plot backgrounds,
  translucent fills, adjusted palette for contrast.
- Data loading: try S3 curated parquet (boto3, cached); fall back to
  committed `data/top_speeds.csv` so HF Spaces keeps working without
  AWS credentials.
- Copy/stats updated for 72+ matches (hero, README).

### 4. Bug audit

Run the app on the refreshed data and fix everything found. Known
suspects going in:

- `@st.cache_data` chart functions close over module globals (`df`,
  `TEAMS_BY_MEAN`) with a hand-built cache key — fragile; pass data
  explicitly.
- Click-to-hide dumbbell state machine (`slope_hidden` / `slope_key`)
  interaction with reruns and filter changes.
- KPI and chart edge cases under narrow filters (single team/match,
  KDE with <2 points).
- README top-20 tables and counts stale (48 matches → 72+).

## Error handling

- Scraper: per-PDF failures logged, don't abort the run; Dagster
  retries partitioned downloads.
- Parsing: rows failing validation dropped with a logged count; a
  match yielding 0 rows fails loudly (format change signal).
- App: S3 unreachable → silent fallback to local CSV.

## Testing

- Unit tests for parsing (`decode`, `extract_match_name`,
  `parse_physical_page` on a fixture) and validation.
- Dagster asset tests with mocked S3.
- Manual verification: `terraform apply`, full backfill run, row counts
  vs expected (72 matches × ~31 players), app run + visual/interaction
  check on desktop and mobile widths.

## Out of scope

- Running Dagster in AWS (stays local for now).
- Rebuilding the app off Streamlit.
- Historical tournaments other than WC 2026.
