"""Parse FIFA match report PDFs: custom-font decode + physical data extraction."""

import io
import logging
import re

import pdfplumber

# pdfminer logs a FontBBox warning per page of these PDFs; drown it out
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# Custom PDF font: U+E071..U+E07A -> digits '0'..'9', U+E094 -> '.'
_DECODE = str.maketrans({chr(0xE071 + i): str(i) for i in range(10)} | {chr(0xE094): "."})
# First private-use-area character marks the start of the encoded stats columns
_PUA = re.compile(r"[-]")

SPEED_MIN, SPEED_MAX = 15.0, 40.0


def decode(s: str) -> str:
    return s.translate(_DECODE)


def extract_match_name(filename: str) -> str:
    """Turn 'PMSR-M03-CAN-V-BIH-V2' -> 'CAN V BIH'."""
    name = re.sub(r"^PMSR-M\d+[-\s]+", "", filename, flags=re.IGNORECASE)
    name = re.sub(r"-V\d+$", "", name, flags=re.IGNORECASE)
    return name.replace("-", " ").strip()


def parse_physical_text(text: str, match_name: str) -> list[dict]:
    """Extract player name + top speed rows from one physical-data page's text."""
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
        stats_str = line[pua.start():].strip()

        pm = re.match(r"^(\d+)\s+(.+)$", prefix)  # "<jersey#> <Player Name>"
        if not pm:
            continue

        tokens = stats_str.split()
        if not tokens:
            continue
        try:
            top_speed = float(decode(tokens[-1]))
        except ValueError:
            top_speed = None

        rows.append({
            "match": match_name,
            "team": team,
            "jersey": int(pm.group(1)),
            "player": pm.group(2).strip(),
            "top_speed_kmh": top_speed,
        })
    return rows


def parse_pdf(data: bytes, match_name: str) -> list[dict]:
    """Parse every page containing a 'Physical Data' section."""
    rows = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "Physical Data" in text:
                rows.extend(parse_physical_text(text, match_name))
    return rows


def validate_rows(rows: list[dict]) -> tuple[list[dict], int]:
    """Keep rows with non-empty match/team/player and speed in range (or None)."""
    kept = []
    for r in rows:
        if not (r["match"] and r["team"] and r["player"]):
            continue
        s = r["top_speed_kmh"]
        if s is not None and not (SPEED_MIN <= s <= SPEED_MAX):
            continue
        kept.append(r)
    return kept, len(rows) - len(kept)
