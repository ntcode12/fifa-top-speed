"""Dagster assets: FIFA hub scrape -> raw PDFs in S3 -> curated top speeds."""

import io
from pathlib import Path

import dagster as dg
import polars as pl
import requests
from bs4 import BeautifulSoup

from pipeline import parsing, storage

BASE_URL = "https://www.fifatrainingcentre.com"
HUB_URLS = [
    f"{BASE_URL}/en/fifa-world-cup-2026/match-report-hub.php",
    f"{BASE_URL}/en/fifa-world-cup-2026/match-report-hub-knockout-stage.php",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

RAW_PREFIX = "raw/pdfs/"
CURATED_KEY = "curated/top_speeds.parquet"
LOCAL_CSV = Path("data/top_speeds.csv")
WEB_JSON = Path("web/src/data/top_speeds.json")


@dg.asset
def match_report_urls(context: dg.AssetExecutionContext) -> list[str]:
    """All match-report PDF URLs listed on the FIFA hub pages (group + knockout)."""
    found: set[str] = set()
    for hub_url in HUB_URLS:
        r = requests.get(hub_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        found |= {
            BASE_URL + a["href"] if a["href"].startswith("/") else a["href"]
            for a in soup.find_all("a", href=True)
            if ".pdf" in a["href"].lower()
        }
    urls = sorted(found)
    context.log.info(f"Found {len(urls)} PDFs across {len(HUB_URLS)} hub pages")
    context.add_output_metadata({"num_pdfs": len(urls)})
    return urls


@dg.asset
def raw_match_pdfs(context: dg.AssetExecutionContext,
                   match_report_urls: list[str]) -> list[str]:
    """Download PDFs not yet in S3 raw zone (append-only). Returns all raw keys."""
    existing = set(storage.list_keys(RAW_PREFIX))
    downloaded = 0
    for url in match_report_urls:
        filename = url.rsplit("/", 1)[-1]
        key = RAW_PREFIX + filename
        if key in existing:
            continue
        try:
            r = requests.get(url, headers=HEADERS, timeout=90)
            r.raise_for_status()
            storage.upload_bytes(key, r.content)
            existing.add(key)
            downloaded += 1
            context.log.info(f"Downloaded {filename}")
        except requests.RequestException as exc:
            context.log.error(f"Failed to fetch {url}: {exc}")
    context.add_output_metadata({"downloaded": downloaded, "total_raw": len(existing)})
    return sorted(existing)


@dg.asset
def top_speeds(context: dg.AssetExecutionContext,
               raw_match_pdfs: list[str]) -> None:
    """Parse all raw PDFs -> validated table -> S3 parquet + local CSV."""
    rows: list[dict] = []
    for key in raw_match_pdfs:
        filename = key.removeprefix(RAW_PREFIX).removesuffix(".pdf")
        match_name = parsing.extract_match_name(filename)
        pdf_rows = parsing.parse_pdf(storage.download_bytes(key), match_name)
        if not pdf_rows:
            raise dg.Failure(f"0 rows parsed from {key} — PDF format changed?")
        rows.extend(pdf_rows)

    kept, dropped = parsing.validate_rows(rows)
    if dropped:
        context.log.warning(f"Dropped {dropped} invalid rows")

    df = pl.DataFrame(kept).sort(["match", "team", "jersey"])
    buf = io.BytesIO()
    df.write_parquet(buf)
    storage.upload_bytes(CURATED_KEY, buf.getvalue())

    LOCAL_CSV.parent.mkdir(exist_ok=True)
    df.write_csv(LOCAL_CSV)

    WEB_JSON.parent.mkdir(parents=True, exist_ok=True)
    df.drop_nulls("top_speed_kmh").write_json(WEB_JSON)

    context.add_output_metadata({
        "rows": len(df),
        "matches": df["match"].n_unique(),
        "max_speed": float(df["top_speed_kmh"].max()),
    })
