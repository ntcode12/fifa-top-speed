# FIFA World Cup 2026 — Top Speed Report

Scraped from the [FIFA Training Centre match report hubs](https://www.fifatrainingcentre.com/en/fifa-world-cup-2026/match-report-hub.php) (group + knockout stage).
**85 matches · 48 teams · 2,683 player records** — refreshed daily by a Dagster pipeline as new match reports publish.

**Live app: [fifa-top-speed.vercel.app](https://fifa-top-speed.vercel.app)** — Next.js explorer in `web/`. Run locally with `cd web && npm run dev`.

---

## Pipeline

Dagster + S3 (Terraform-provisioned, bucket `fifa-topspeed-<account>`):

- `uv run dagster dev` — UI with lineage, manual runs, daily schedule
- `uv run dagster asset materialize -m pipeline.definitions --select '*'` — one-shot refresh
- Assets: `match_report_urls` → `raw_match_pdfs` (incremental, append-only raw zone) → `top_speeds` (parquet in S3 + `data/top_speeds.csv` fallback)
- `terraform -chdir=infra apply` — provision the bucket

The web app is statically built from `web/src/data/top_speeds.json`, which the
pipeline refreshes alongside the S3 parquet — push to `main` and Vercel redeploys
with the new data.

---

## Top 20 Fastest Recorded Speeds

| # | Player | Team | Match | km/h |
|---|--------|------|-------|-----:|
| 🥇 | Kylian MBAPPE | France | NOR V FRA | **37.6** |
| 🥈 | Anthony ELANGA | Sweden | FRA V SWE | **37.2** |
| 🥉 | Micky VAN DE VEN | Netherlands | NED V SWE | **36.8** |
| 4 | Jordan BOS | Australia | AUS V TUR | 36.7 |
| 5 | Erling HAALAND | Norway | IRQ V NOR | 36.5 |
| 6 | Anthony ELANGA | Sweden | NED V SWE | 36.5 |
| 7 | Abdukodir KHUSANOV | Uzbekistan | UZB V COL | 36.5 |
| 8 | Bradley BARCOLA | France | NOR V FRA | 36.3 |
| 9 | NELSON SEMEDO | Portugal | POR V CRO | 35.9 |
| 10 | Mohamed TOURE | Australia | AUS V TUR | 35.8 |
| 11 | Micky VAN DE VEN | Netherlands | NED V MAR | 35.8 |
| 12 | Ryan GRAVENBERCH | Netherlands | NED V JPN | 35.6 |
| 13 | Marcus HOLMGREN PEDERSEN | Norway | NOR V FRA | 35.6 |
| 14 | Abdukodir KHUSANOV | Uzbekistan | POR V GHA | 35.6 |
| 15 | Alan MINDA | Ecuador | CIV V ECU | 35.5 |
| 16 | Achraf HAKIMI | Morocco | NED V MAR | 35.5 |
| 17 | Sondre LANGAS | Norway | NOR V FRA | 35.5 |
| 18 | Dayot UPAMECANO | France | FRA V SWE | 35.4 |
| 19 | PEDRO NETO | Portugal | COL V POR | 35.3 |
| 20 | Marcus RASHFORD | England | ENG V COD | 35.2 |

## Top 20 Fastest Recorded Speeds (mph)

| # | Player | Team | Match | mph |
|---|--------|------|-------|----:|
| 🥇 | Kylian MBAPPE | France | NOR V FRA | **23.4** |
| 🥈 | Anthony ELANGA | Sweden | FRA V SWE | **23.1** |
| 🥉 | Micky VAN DE VEN | Netherlands | NED V SWE | **22.9** |
| 4 | Jordan BOS | Australia | AUS V TUR | 22.8 |
| 5 | Erling HAALAND | Norway | IRQ V NOR | 22.7 |
| 6 | Anthony ELANGA | Sweden | NED V SWE | 22.7 |
| 7 | Abdukodir KHUSANOV | Uzbekistan | UZB V COL | 22.7 |
| 8 | Bradley BARCOLA | France | NOR V FRA | 22.6 |
| 9 | NELSON SEMEDO | Portugal | POR V CRO | 22.3 |
| 10 | Mohamed TOURE | Australia | AUS V TUR | 22.2 |
| 11 | Micky VAN DE VEN | Netherlands | NED V MAR | 22.2 |
| 12 | Ryan GRAVENBERCH | Netherlands | NED V JPN | 22.1 |
| 13 | Marcus HOLMGREN PEDERSEN | Norway | NOR V FRA | 22.1 |
| 14 | Abdukodir KHUSANOV | Uzbekistan | POR V GHA | 22.1 |
| 15 | Alan MINDA | Ecuador | CIV V ECU | 22.1 |
| 16 | Achraf HAKIMI | Morocco | NED V MAR | 22.1 |
| 17 | Sondre LANGAS | Norway | NOR V FRA | 22.1 |
| 18 | Dayot UPAMECANO | France | FRA V SWE | 22.0 |
| 19 | PEDRO NETO | Portugal | COL V POR | 21.9 |
| 20 | Marcus RASHFORD | England | ENG V COD | 21.9 |

---

## Files

| File | Description |
|------|-------------|
| `web/` | Next.js explorer (liquid glass theme) — deployed on Vercel |
| `pipeline/` | Dagster assets: scrape hub → raw PDFs to S3 → curated parquet + web JSON |
| `infra/` | Terraform: S3 bucket (versioned, encrypted, private) |
| `data/top_speeds.csv` | Full dataset (2,683 rows) |
| `charts.py` | Generates all 5 static PNGs |
| `tests/` | Unit tests (parsing, storage, Dagster definitions) |
