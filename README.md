---
title: FIFA WC 2026 Top Speeds
emoji: ⚡
colorFrom: indigo
colorTo: red
sdk: docker
app_port: 8501
pinned: false
---

# FIFA World Cup 2026 — Top Speed Report

Scraped from the [FIFA Training Centre match report hub](https://www.fifatrainingcentre.com/en/fifa-world-cup-2026/match-report-hub.php).  
**48 matches · 48 teams · 1,512 player records**

Live app: interactive Streamlit explorer (`app.py`). Run locally with `uv run streamlit run app.py`.

---

## Top 20 Fastest Recorded Speeds

| # | Player | Team | Match | km/h |
|---|--------|------|-------|-----:|
| 🥇 | Micky VAN DE VEN | Netherlands | NED V SWE | **36.8** |
| 🥈 | Jordan BOS | Australia | AUS V TUR | **36.7** |
| 🥉 | Anthony ELANGA | Sweden | NED V SWE | **36.5** |
| 4 | Erling HAALAND | Norway | IRQ V NOR | 36.5 |
| 5 | Abdukodir KHUSANOV | Uzbekistan | UZB V COL | 36.5 |
| 6 | Mohamed TOURE | Australia | AUS V TUR | 35.8 |
| 7 | Ryan GRAVENBERCH | Netherlands | NED V JPN | 35.6 |
| 8 | Abdukodir KHUSANOV | Uzbekistan | POR V GHA | 35.6 |
| 9 | Alan MINDA | Ecuador | CIV V ECU | 35.5 |
| 10 | SON Heungmin | Korea Republic | KOR V CZE | 35.2 |
| 11 | Erling HAALAND | Norway | NOR V SEN | 35.2 |
| 12 | Djed SPENCE | England | ENG V CRO | 35.2 |
| 13 | Achraf HAKIMI | Morocco | SCO V MAR | 35.1 |
| 14 | Kylian MBAPPE | France | FRA V SEN | 35.1 |
| 15 | Antoine SEMENYO | Ghana | ENG V GHA | 35.1 |
| 16 | Felix NMECHA | Germany | GER V CIV | 35.0 |
| 17 | PICO LOPES | Cabo Verde | URU V CPV | 35.0 |
| 18 | Brian RODRIGUEZ | Uruguay | URU V CPV | 34.9 |
| 19 | Esmir BAJRAKTAREVIC | Bosnia and Herzegovina | CAN V BIH | 34.8 |
| 20 | Nestory IRANKUNDA | Australia | USA V AUS | 34.8 |

## Top 20 Fastest Recorded Speeds (mph)

| # | Player | Team | Match | mph |
|---|--------|------|-------|----:|
| 🥇 | Micky VAN DE VEN | Netherlands | NED V SWE | **22.9** |
| 🥈 | Jordan BOS | Australia | AUS V TUR | **22.8** |
| 🥉 | Anthony ELANGA | Sweden | NED V SWE | **22.7** |
| 4 | Erling HAALAND | Norway | IRQ V NOR | 22.7 |
| 5 | Abdukodir KHUSANOV | Uzbekistan | UZB V COL | 22.7 |
| 6 | Mohamed TOURE | Australia | AUS V TUR | 22.2 |
| 7 | Ryan GRAVENBERCH | Netherlands | NED V JPN | 22.1 |
| 8 | Abdukodir KHUSANOV | Uzbekistan | POR V GHA | 22.1 |
| 9 | Alan MINDA | Ecuador | CIV V ECU | 22.1 |
| 10 | SON Heungmin | Korea Republic | KOR V CZE | 21.9 |
| 11 | Erling HAALAND | Norway | NOR V SEN | 21.9 |
| 12 | Djed SPENCE | England | ENG V CRO | 21.9 |
| 13 | Achraf HAKIMI | Morocco | SCO V MAR | 21.8 |
| 14 | Kylian MBAPPE | France | FRA V SEN | 21.8 |
| 15 | Antoine SEMENYO | Ghana | ENG V GHA | 21.8 |
| 16 | Felix NMECHA | Germany | GER V CIV | 21.7 |
| 17 | PICO LOPES | Cabo Verde | URU V CPV | 21.7 |
| 18 | Brian RODRIGUEZ | Uruguay | URU V CPV | 21.7 |
| 19 | Esmir BAJRAKTAREVIC | Bosnia and Herzegovina | CAN V BIH | 21.6 |
| 20 | Nestory IRANKUNDA | Australia | USA V AUS | 21.6 |

---

## Files

| File | Description |
|------|-------------|
| `main.py` | Scraper — fetches all 48 PDFs and extracts player + top speed data |
| `charts.py` | Generates all 5 static PNGs |
| `top_speeds.csv` | Full dataset (1,512 rows) |
| `exports/1_beeswarm.png` | Every player, every match |
| `exports/2_distribution.png` | Tournament speed distribution |
| `exports/3_teams.png` | Team speed ranges |
| `exports/4_leaderboard.png` | Top 25 player leaderboard |
| `exports/5_delta.png` | Biggest speed swings between matches |
