# FIFA World Cup 2026 — Top Speed Report

Scraped from the [FIFA Training Centre match report hub](https://www.fifatrainingcentre.com/en/fifa-world-cup-2026/match-report-hub.php).
**72 matches · 48 teams · 2,271 player records** — refreshed daily by a Dagster pipeline as new match reports publish.

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
| 🥈 | Micky VAN DE VEN | Netherlands | NED V SWE | **36.8** |
| 🥉 | Jordan BOS | Australia | AUS V TUR | **36.7** |
| 4 | Erling HAALAND | Norway | IRQ V NOR | 36.5 |
| 5 | Anthony ELANGA | Sweden | NED V SWE | 36.5 |
| 6 | Abdukodir KHUSANOV | Uzbekistan | UZB V COL | 36.5 |
| 7 | Bradley BARCOLA | France | NOR V FRA | 36.3 |
| 8 | Mohamed TOURE | Australia | AUS V TUR | 35.8 |
| 9 | Ryan GRAVENBERCH | Netherlands | NED V JPN | 35.6 |
| 10 | Marcus HOLMGREN PEDERSEN | Norway | NOR V FRA | 35.6 |
| 11 | Abdukodir KHUSANOV | Uzbekistan | POR V GHA | 35.6 |
| 12 | Alan MINDA | Ecuador | CIV V ECU | 35.5 |
| 13 | Sondre LANGAS | Norway | NOR V FRA | 35.5 |
| 14 | PEDRO NETO | Portugal | COL V POR | 35.3 |
| 15 | Djed SPENCE | England | ENG V CRO | 35.2 |
| 16 | Giuliano SIMEONE | Argentina | JOR V ARG | 35.2 |
| 17 | SON Heungmin | Korea Republic | KOR V CZE | 35.2 |
| 18 | Erling HAALAND | Norway | NOR V SEN | 35.2 |
| 19 | Richie LARYEA | Canada | SUI V CAN | 35.2 |
| 20 | Antoine SEMENYO | Ghana | ENG V GHA | 35.1 |

## Top 20 Fastest Recorded Speeds (mph)

| # | Player | Team | Match | mph |
|---|--------|------|-------|----:|
| 🥇 | Kylian MBAPPE | France | NOR V FRA | **23.4** |
| 🥈 | Micky VAN DE VEN | Netherlands | NED V SWE | **22.9** |
| 🥉 | Jordan BOS | Australia | AUS V TUR | **22.8** |
| 4 | Erling HAALAND | Norway | IRQ V NOR | 22.7 |
| 5 | Anthony ELANGA | Sweden | NED V SWE | 22.7 |
| 6 | Abdukodir KHUSANOV | Uzbekistan | UZB V COL | 22.7 |
| 7 | Bradley BARCOLA | France | NOR V FRA | 22.6 |
| 8 | Mohamed TOURE | Australia | AUS V TUR | 22.2 |
| 9 | Ryan GRAVENBERCH | Netherlands | NED V JPN | 22.1 |
| 10 | Marcus HOLMGREN PEDERSEN | Norway | NOR V FRA | 22.1 |
| 11 | Abdukodir KHUSANOV | Uzbekistan | POR V GHA | 22.1 |
| 12 | Alan MINDA | Ecuador | CIV V ECU | 22.1 |
| 13 | Sondre LANGAS | Norway | NOR V FRA | 22.1 |
| 14 | PEDRO NETO | Portugal | COL V POR | 21.9 |
| 15 | Djed SPENCE | England | ENG V CRO | 21.9 |
| 16 | Giuliano SIMEONE | Argentina | JOR V ARG | 21.9 |
| 17 | SON Heungmin | Korea Republic | KOR V CZE | 21.9 |
| 18 | Erling HAALAND | Norway | NOR V SEN | 21.9 |
| 19 | Richie LARYEA | Canada | SUI V CAN | 21.9 |
| 20 | Antoine SEMENYO | Ghana | ENG V GHA | 21.8 |

---

## Files

| File | Description |
|------|-------------|
| `web/` | Next.js explorer (liquid glass theme) — deployed on Vercel |
| `pipeline/` | Dagster assets: scrape hub → raw PDFs to S3 → curated parquet + web JSON |
| `infra/` | Terraform: S3 bucket (versioned, encrypted, private) |
| `data/top_speeds.csv` | Full dataset (2,271 rows) |
| `charts.py` | Generates all 5 static PNGs |
| `tests/` | Unit tests (parsing, storage, Dagster definitions) |
