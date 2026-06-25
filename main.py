"""FIFA World Cup 2026 player top speed scraper."""

import io
import re
import sys

import pdfplumber
import polars as pl
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.fifatrainingcentre.com"
HUB_URL = f"{BASE_URL}/en/fifa-world-cup-2026/match-report-hub.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Custom PDF font: U+E071..U+E07A → digits '0'..'9', U+E094 → '.'
_DECODE = str.maketrans({chr(0xE071 + i): str(i) for i in range(10)} | {chr(0xE094): "."})
# Regex to find the first private-use-area character (start of encoded stats)
_PUA = re.compile(r"[-]")


def decode(s: str) -> str:
    return s.translate(_DECODE)


def get_pdf_links() -> list[str]:
    r = requests.get(HUB_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            links.append(BASE_URL + href if href.startswith("/") else href)
    return links


def extract_match_name(filename: str) -> str:
    """Turn 'PMSR-M03-CAN-V-BIH-V2' → 'CAN V BIH'."""
    name = re.sub(r"^PMSR-M\d+[-\s]+", "", filename, flags=re.IGNORECASE)
    name = re.sub(r"-V\d+$", "", name, flags=re.IGNORECASE)
    return name.replace("-", " ").strip()


def parse_physical_page(page, match_name: str) -> list[dict]:
    """Extract player name + top speed from a single physical data page."""
    text = page.extract_text() or ""

    team = ""
    m = re.search(r"Physical Data (.+)", text)
    if m:
        team = m.group(1).strip()

    rows = []
    for line in text.split("\n"):
        pua = _PUA.search(line)
        if pua is None:
            continue
        prefix = line[: pua.start()].strip()
        stats_str = line[pua.start() :].strip()

        # prefix must be "<jersey#> <Player Name>"
        pm = re.match(r"^(\d+)\s+(.+)$", prefix)
        if not pm:
            continue

        jersey = int(pm.group(1))
        player = pm.group(2).strip()

        tokens = stats_str.split()
        if not tokens:
            continue

        top_speed_raw = decode(tokens[-1])
        try:
            top_speed = float(top_speed_raw)
        except ValueError:
            top_speed = None

        rows.append(
            {
                "match": match_name,
                "team": team,
                "jersey": jersey,
                "player": player,
                "top_speed_kmh": top_speed,
            }
        )
    return rows


def process_pdf(url: str) -> list[dict]:
    filename = url.rsplit("/", 1)[-1].removesuffix(".pdf")
    match_name = extract_match_name(filename)

    r = requests.get(url, headers=HEADERS, timeout=90)
    r.raise_for_status()

    records = []
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        n = len(pdf.pages)
        # 3rd-to-last and 2nd-to-last pages hold Team A and Team B physical data
        for idx in [n - 3, n - 2]:
            if 0 <= idx < n:
                records.extend(parse_physical_page(pdf.pages[idx], match_name))
    return records


def main() -> None:
    print("Fetching PDF links...", flush=True)
    links = get_pdf_links()
    print(f"Found {len(links)} PDFs\n", flush=True)

    all_records: list[dict] = []
    for i, url in enumerate(links, 1):
        name = url.rsplit("/", 1)[-1]
        print(f"[{i:>2}/{len(links)}] {name}", flush=True)
        try:
            records = process_pdf(url)
            all_records.extend(records)
            print(f"         → {len(records)} players", flush=True)
        except Exception as exc:
            print(f"         ERROR: {exc}", file=sys.stderr, flush=True)

    df = pl.DataFrame(all_records)
    print(f"\nTotal player-rows: {len(df)}")
    print(df)

    out = "top_speeds.csv"
    df.write_csv(out)
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    main()
