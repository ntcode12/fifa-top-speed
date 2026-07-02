# Liquid Glass Redesign + Dagster Pipeline + S3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Terraform-provisioned S3 storage, an incremental Dagster pipeline that backfills all available FIFA WC 2026 match reports, and a liquid-glass redesign of the Streamlit app with bugs fixed.

**Architecture:** One S3 bucket (`raw/pdfs/` for immutable PDFs, `curated/` for parquet). Dagster assets: scrape hub URLs → download missing PDFs to S3 → parse all PDFs → curated parquet in S3 + committed local CSV fallback. Streamlit app reads S3 parquet, falls back to `data/top_speeds.csv`.

**Tech Stack:** Python 3.13, uv, polars, pdfplumber, Dagster, boto3, moto (tests), pytest, Terraform 1.11, Streamlit + Plotly.

## Global Constraints

- AWS account `032968994565`, region `us-east-1`. Bucket name: `fifa-topspeed-032968994565`, overridable via env var `FIFA_BUCKET`.
- Python `>=3.13`, managed with `uv` (`uv add`, `uv run`).
- The app MUST keep working with no AWS credentials (HF Spaces): any S3 failure falls back silently to `data/top_speeds.csv`.
- Never delete or overwrite objects under `raw/pdfs/` — raw zone is append-only.
- All commits end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Terraform S3 bucket

**Files:**
- Create: `infra/main.tf`, `infra/.gitignore`
- Modify: `.gitignore` (nothing needed — infra has its own)

**Interfaces:**
- Produces: S3 bucket `fifa-topspeed-032968994565` (versioned, encrypted, private). Terraform output `bucket_name`.

- [ ] **Step 1: Write Terraform config**

`infra/main.tf`:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "fifa" {
  bucket = "fifa-topspeed-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "fifa" {
  bucket = aws_s3_bucket.fifa.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "fifa" {
  bucket = aws_s3_bucket.fifa.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "fifa" {
  bucket                  = aws_s3_bucket.fifa.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_name" {
  value = aws_s3_bucket.fifa.bucket
}
```

`infra/.gitignore`:

```
.terraform/
*.tfstate
*.tfstate.backup
.terraform.lock.hcl
```

- [ ] **Step 2: Init and validate**

Run: `terraform -chdir=infra init && terraform -chdir=infra validate`
Expected: `Success! The configuration is valid.`

- [ ] **Step 3: Apply**

Run: `terraform -chdir=infra apply -auto-approve`
Expected: `Apply complete! Resources: 4 added` and output `bucket_name = "fifa-topspeed-032968994565"`

- [ ] **Step 4: Verify bucket exists**

Run: `aws s3api head-bucket --bucket fifa-topspeed-032968994565 && echo OK`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add infra/
git commit -m "Provision S3 bucket with Terraform (versioned, encrypted, private)"
```

---

### Task 2: Parsing module with tests

**Files:**
- Create: `pipeline/__init__.py` (empty), `pipeline/parsing.py`, `tests/__init__.py` (empty), `tests/test_parsing.py`
- Reference (do not delete yet): `main.py`

**Interfaces:**
- Produces:
  - `decode(s: str) -> str` — translates the PDF's private-use-area font chars to digits/dot.
  - `extract_match_name(filename: str) -> str` — `"PMSR-M03-CAN-V-BIH-V2"` → `"CAN V BIH"`.
  - `parse_physical_text(text: str, match_name: str) -> list[dict]` — rows with keys `match, team, jersey, player, top_speed_kmh` from one page's text.
  - `parse_pdf(data: bytes, match_name: str) -> list[dict]` — scans ALL pages whose text contains `"Physical Data"` (robust to knockout PDFs having different page counts).
  - `validate_rows(rows: list[dict]) -> tuple[list[dict], int]` — (kept rows, dropped count). Drops rows with empty player/team/match or speed outside 15–40 (None speed is kept).

- [ ] **Step 1: Add dev/pipeline dependencies**

Run: `uv add boto3 dagster dagster-webserver && uv add --dev pytest moto`
Expected: resolves and updates `pyproject.toml` + `uv.lock` without error.

- [ ] **Step 2: Write failing tests**

`tests/test_parsing.py`:

```python
from pipeline.parsing import (
    decode,
    extract_match_name,
    parse_physical_text,
    validate_rows,
)

# The PDF font maps U+E071..U+E07A -> '0'..'9' and U+E094 -> '.'
def enc(s: str) -> str:
    table = {str(i): chr(0xE071 + i) for i in range(10)} | {".": chr(0xE094)}
    return "".join(table.get(c, c) for c in s)


def test_decode_digits_and_dot():
    assert decode(enc("36.8")) == "36.8"


def test_extract_match_name():
    assert extract_match_name("PMSR-M03-CAN-V-BIH-V2") == "CAN V BIH"
    assert extract_match_name("PMSR-M101-NED-V-SWE") == "NED V SWE"


def test_parse_physical_text():
    text = "\n".join([
        "Physical Data Netherlands",
        f"4 Micky VAN DE VEN {enc('10.2')} {enc('1.4')} {enc('36.8')}",
        "some non-player line",
        f"11 Anthony ELANGA {enc('9.9')} {enc('1.1')} {enc('36.5')}",
    ])
    rows = parse_physical_text(text, "NED V SWE")
    assert rows == [
        {"match": "NED V SWE", "team": "Netherlands", "jersey": 4,
         "player": "Micky VAN DE VEN", "top_speed_kmh": 36.8},
        {"match": "NED V SWE", "team": "Netherlands", "jersey": 11,
         "player": "Anthony ELANGA", "top_speed_kmh": 36.5},
    ]


def test_validate_rows_drops_bad_speed_and_empty_fields():
    good = {"match": "A V B", "team": "X", "jersey": 1, "player": "P", "top_speed_kmh": 30.0}
    none_speed = good | {"top_speed_kmh": None}
    too_fast = good | {"top_speed_kmh": 55.0}
    no_player = good | {"player": ""}
    kept, dropped = validate_rows([good, none_speed, too_fast, no_player])
    assert kept == [good, none_speed]
    assert dropped == 2
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_parsing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline'` (or ImportError).

- [ ] **Step 4: Implement `pipeline/parsing.py`**

Port from `main.py`, refactored so page parsing takes text, plus new `parse_pdf` (scans all pages) and `validate_rows`:

```python
"""Parse FIFA match report PDFs: custom-font decode + physical data extraction."""

import io
import re

import pdfplumber

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
```

Also create empty `pipeline/__init__.py` and `tests/__init__.py`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_parsing.py -v`
Expected: 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add pipeline/ tests/ pyproject.toml uv.lock
git commit -m "Extract PDF parsing into tested pipeline.parsing module"
```

---

### Task 3: S3 storage module

**Files:**
- Create: `pipeline/storage.py`, `tests/test_storage.py`

**Interfaces:**
- Produces:
  - `bucket_name() -> str` — env `FIFA_BUCKET`, default `"fifa-topspeed-032968994565"`.
  - `object_exists(key: str) -> bool`
  - `upload_bytes(key: str, data: bytes) -> None`
  - `download_bytes(key: str) -> bytes`
  - `list_keys(prefix: str) -> list[str]`

- [ ] **Step 1: Write failing tests**

`tests/test_storage.py`:

```python
import boto3
import pytest
from moto import mock_aws

from pipeline import storage


def test_bucket_name_env_override(monkeypatch):
    monkeypatch.setenv("FIFA_BUCKET", "custom-bucket")
    assert storage.bucket_name() == "custom-bucket"
    monkeypatch.delenv("FIFA_BUCKET")
    assert storage.bucket_name() == "fifa-topspeed-032968994565"


@pytest.fixture
def s3_bucket(monkeypatch):
    monkeypatch.setenv("FIFA_BUCKET", "test-bucket")
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
        yield


def test_roundtrip_and_exists(s3_bucket):
    assert not storage.object_exists("raw/pdfs/x.pdf")
    storage.upload_bytes("raw/pdfs/x.pdf", b"hello")
    assert storage.object_exists("raw/pdfs/x.pdf")
    assert storage.download_bytes("raw/pdfs/x.pdf") == b"hello"
    assert storage.list_keys("raw/pdfs/") == ["raw/pdfs/x.pdf"]
    assert storage.list_keys("curated/") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_storage.py -v`
Expected: FAIL with ImportError (`pipeline.storage` missing).

- [ ] **Step 3: Implement `pipeline/storage.py`**

```python
"""Thin S3 helpers for the FIFA top-speed pipeline."""

import os

import boto3
from botocore.exceptions import ClientError

DEFAULT_BUCKET = "fifa-topspeed-032968994565"


def bucket_name() -> str:
    return os.environ.get("FIFA_BUCKET", DEFAULT_BUCKET)


def _client():
    return boto3.client("s3")


def object_exists(key: str) -> bool:
    try:
        _client().head_object(Bucket=bucket_name(), Key=key)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def upload_bytes(key: str, data: bytes) -> None:
    _client().put_object(Bucket=bucket_name(), Key=key, Body=data)


def download_bytes(key: str) -> bytes:
    return _client().get_object(Bucket=bucket_name(), Key=key)["Body"].read()


def list_keys(prefix: str) -> list[str]:
    paginator = _client().get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=bucket_name(), Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_storage.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add pipeline/storage.py tests/test_storage.py
git commit -m "Add S3 storage helpers with moto tests"
```

---

### Task 4: Dagster assets, definitions, schedule

**Files:**
- Create: `pipeline/assets.py`, `pipeline/definitions.py`, `tests/test_definitions.py`
- Modify: `pyproject.toml` (add `[tool.dagster]` section)

**Interfaces:**
- Consumes: `pipeline.parsing` (`extract_match_name`, `parse_pdf`, `validate_rows`), `pipeline.storage` (all helpers).
- Produces: Dagster assets `match_report_urls`, `raw_match_pdfs`, `top_speeds`; job `refresh_all`; daily schedule. S3 object `curated/top_speeds.parquet`; local file `data/top_speeds.csv`.

- [ ] **Step 1: Write failing test**

`tests/test_definitions.py`:

```python
from dagster import AssetKey

from pipeline.definitions import defs


def test_definitions_load():
    keys = {spec.key for spec in defs.get_all_asset_specs()}
    assert {AssetKey("match_report_urls"), AssetKey("raw_match_pdfs"),
            AssetKey("top_speeds")} <= keys
    assert defs.get_schedule_def("daily_refresh") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_definitions.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `pipeline/assets.py`**

```python
"""Dagster assets: FIFA hub scrape -> raw PDFs in S3 -> curated top speeds."""

import io
from pathlib import Path

import dagster as dg
import polars as pl
import requests
from bs4 import BeautifulSoup

from pipeline import parsing, storage

BASE_URL = "https://www.fifatrainingcentre.com"
HUB_URL = f"{BASE_URL}/en/fifa-world-cup-2026/match-report-hub.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

RAW_PREFIX = "raw/pdfs/"
CURATED_KEY = "curated/top_speeds.parquet"
LOCAL_CSV = Path("data/top_speeds.csv")


@dg.asset
def match_report_urls(context: dg.AssetExecutionContext) -> list[str]:
    """All match-report PDF URLs currently listed on the FIFA hub page."""
    r = requests.get(HUB_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    urls = sorted({
        BASE_URL + a["href"] if a["href"].startswith("/") else a["href"]
        for a in soup.find_all("a", href=True)
        if ".pdf" in a["href"].lower()
    })
    context.log.info(f"Found {len(urls)} PDFs on hub")
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

    context.add_output_metadata({
        "rows": len(df),
        "matches": df["match"].n_unique(),
        "max_speed": float(df["top_speed_kmh"].max()),
    })
```

- [ ] **Step 4: Implement `pipeline/definitions.py`**

```python
import dagster as dg

from pipeline.assets import match_report_urls, raw_match_pdfs, top_speeds

refresh_all = dg.define_asset_job("refresh_all", selection="*")

daily_refresh = dg.ScheduleDefinition(
    name="daily_refresh",
    job=refresh_all,
    cron_schedule="0 6 * * *",  # 06:00 daily
)

defs = dg.Definitions(
    assets=[match_report_urls, raw_match_pdfs, top_speeds],
    jobs=[refresh_all],
    schedules=[daily_refresh],
)
```

Add to `pyproject.toml`:

```toml
[tool.dagster]
module_name = "pipeline.definitions"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/ -v`
Expected: all PASS (parsing, storage, definitions).

- [ ] **Step 6: Commit**

```bash
git add pipeline/ tests/ pyproject.toml
git commit -m "Add Dagster assets, job, and daily schedule"
```

---

### Task 5: Run the backfill, retire old scripts

**Files:**
- Delete: `main.py`
- Move: `top_speeds.csv` → `data/top_speeds.csv` (regenerated by pipeline)
- Modify: `charts.py` (CSV path), `.gitignore`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: fully backfilled S3 bucket + fresh `data/top_speeds.csv` (72 matches, ~2,200+ rows) committed.

- [ ] **Step 1: Materialize all assets**

Run: `uv run dagster asset materialize -m pipeline.definitions --select '*'`
Expected: succeeds; logs show 72 PDFs found, 72 downloaded (first run), `data/top_speeds.csv` written.
(If any individual PDF download fails with a network error, re-run — already-downloaded PDFs are skipped.)

- [ ] **Step 2: Verify outputs**

Run:
```bash
aws s3 ls s3://fifa-topspeed-032968994565/raw/pdfs/ | wc -l
aws s3 ls s3://fifa-topspeed-032968994565/curated/
awk -F, 'NR>1{m[$1]++} END{print NR-1" rows, "length(m)" matches"}' data/top_speeds.csv
```
Expected: 72 PDFs; `top_speeds.parquet` present; ~2,200+ rows across 72 matches.

- [ ] **Step 3: Retire old scraper, fix charts path**

```bash
git rm main.py
git rm --cached top_speeds.csv && rm top_speeds.csv
```
In `charts.py`, replace `top_speeds.csv` with `data/top_speeds.csv` (single `read_csv` call near the top).

- [ ] **Step 4: Run remaining tests**

Run: `uv run pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Backfill 72 matches via Dagster; retire one-shot scraper"
```

---

### Task 6: App data loading — S3 with local fallback, cache fixes

**Files:**
- Modify: `app.py` (data section, lines ~113–152), `requirements.txt` (add `boto3`, `pdfplumber` NOT needed — only `boto3`)

**Interfaces:**
- Consumes: `curated/top_speeds.parquet` in S3; `data/top_speeds.csv` fallback.
- Produces: `load() -> pl.DataFrame` used by the rest of `app.py` unchanged.

- [ ] **Step 1: Replace the data-loading block**

Replace the current `load()` in `app.py` with:

```python
S3_BUCKET = os.environ.get("FIFA_BUCKET", "fifa-topspeed-032968994565")
S3_KEY = "curated/top_speeds.parquet"
LOCAL_CSV = "data/top_speeds.csv"


@st.cache_data(ttl=3600, show_spinner=False)
def load() -> pl.DataFrame:
    try:
        import io
        import boto3
        body = boto3.client("s3").get_object(Bucket=S3_BUCKET, Key=S3_KEY)["Body"].read()
        df = pl.read_parquet(io.BytesIO(body))
    except Exception:
        df = pl.read_csv(LOCAL_CSV)
    return df.drop_nulls("top_speed_kmh")
```

Add `import os` at the top of `app.py`. Add `boto3` to `requirements.txt`.

Note the `.drop_nulls("top_speed_kmh")` — fixes null speeds reaching sorts/KDE.

- [ ] **Step 2: Fix stale-cache and hidden-state bugs**

In `app.py`:
- The `cache_key` for chart functions must also reflect the data itself, not just filters. Change to: `cache_key = f"{sel_teams}{sel_matches}{len(df_all)}"`.
- Clear click-to-hide state when filters change: after `cache_key` is computed, add

```python
if st.session_state.get("last_cache_key") != cache_key:
    st.session_state.slope_hidden = set()
    st.session_state.last_cache_key = cache_key
```

(Keep the existing `if "slope_hidden" not in st.session_state` init above it.)

- [ ] **Step 3: Verify app runs with S3**

Run: `uv run streamlit run app.py --server.headless true &` then `sleep 6 && curl -s localhost:8501 | head -1` and check the process log for errors; kill it after.
Expected: HTML response, no traceback; KPI counts reflect 72 matches (spot-check by loading data in a Python one-liner).

- [ ] **Step 4: Verify fallback path**

Run: `AWS_ACCESS_KEY_ID=invalid AWS_SECRET_ACCESS_KEY=invalid AWS_PROFILE= uv run python -c "
import app  # noqa
"` — simpler: `uv run python -c "
import os
os.environ['FIFA_BUCKET'] = 'nonexistent-bucket-xyz'
import polars as pl, io, boto3
try:
    boto3.client('s3').get_object(Bucket='nonexistent-bucket-xyz', Key='x')
except Exception:
    df = pl.read_csv('data/top_speeds.csv')
print(len(df))
"`
Expected: prints row count — confirms the fallback file parses.

- [ ] **Step 5: Commit**

```bash
git add app.py requirements.txt
git commit -m "App loads curated parquet from S3 with local CSV fallback; fix cache/state bugs"
```

---

### Task 7: Liquid glass redesign

**Files:**
- Modify: `app.py` — palette block (lines ~16–25), CSS block (lines ~30–94), `base_layout()` (~156–171), chart color usages.

**Interfaces:**
- Consumes: existing section/KPI/chart structure — unchanged.
- Produces: dark liquid-glass theme. New palette constants (same names, new values) so charts pick them up automatically.

- [ ] **Step 1: Swap the palette**

```python
BG     = "rgba(0,0,0,0)"   # plotly backgrounds transparent — glass shows through
INK    = "#e7ecf5"          # primary text
DIM    = "#8b93a7"          # secondary text
FAINT  = "#5c6478"          # tertiary
RULE   = "rgba(255,255,255,0.09)"  # gridlines / hairlines
INDIGO = "#8b9cf9"          # accent (lightened for dark bg)
ROSE   = "#fb7185"
SLATE  = "#3d4457"
AMBER  = "#fbbf24"
```

`lerp`/`rgba` helpers only accept hex — they are used with `INDIGO`/`SLATE` which stay hex, fine. Check every literal color in `app.py` (`#94a3b8` in annotations, `"#f1f5f9"` inactive connector, hover label colors) and replace: `#94a3b8` → `#8b93a7`, `#f1f5f9` → `rgba(255,255,255,0.05)`. In `slope_fig` the hollow-dot marker uses `BG` as fill — replace that usage with a new constant `DOT_BG = "#141a2e"` so hollow dots stay visible.

In `base_layout`, set `hoverlabel=dict(bgcolor="rgba(20,26,46,0.95)", bordercolor="rgba(255,255,255,0.15)", font=dict(family="Inter", size=12, color=INK))`.

- [ ] **Step 2: Replace the CSS block**

Replace the entire `st.markdown("""<style>...""")` block with:

```python
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, sans-serif;
}
.stApp {
    background: radial-gradient(ellipse 80% 50% at 20% -10%, rgba(99,102,241,0.28), transparent),
                radial-gradient(ellipse 60% 40% at 90% 10%, rgba(225,29,72,0.16), transparent),
                radial-gradient(ellipse 50% 60% at 60% 110%, rgba(56,189,248,0.12), transparent),
                #0b1020;
    background-attachment: fixed;
}
.block-container { padding-top: 2.5rem; padding-bottom: 5rem;
                   padding-left: 2.5rem; padding-right: 2.5rem; max-width: 1180px; }

/* ── glass card primitive ── */
.glass {
    background: linear-gradient(135deg, rgba(255,255,255,0.09), rgba(255,255,255,0.03));
    backdrop-filter: blur(22px) saturate(140%);
    -webkit-backdrop-filter: blur(22px) saturate(140%);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35),
                inset 0 1px 0 rgba(255,255,255,0.12);
}

.hero-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: .16em;
                text-transform: uppercase; color: #8b9cf9; margin-bottom: 12px; }
.hero-title   { font-size: 46px; font-weight: 900; color: #f2f5fb;
                letter-spacing: -1.8px; line-height: 1.04;
                text-shadow: 0 0 40px rgba(139,156,249,0.35); }
.hero-sub     { font-size: 14px; color: #8b93a7; margin-top: 14px;
                font-weight: 400; line-height: 1.6; max-width: 640px; }

.kpi          { padding: 18px 20px; }
.kpi-label    { font-size: 10px; font-weight: 700; letter-spacing: .1em;
                text-transform: uppercase; color: #8b93a7; margin-bottom: 9px; }
.kpi-value    { font-size: 28px; font-weight: 800; color: #f2f5fb;
                letter-spacing: -0.6px; line-height: 1.05; }
.kpi.accent .kpi-value { color: #a5b4fc;
                text-shadow: 0 0 24px rgba(139,156,249,0.5); }
.kpi-sub      { font-size: 11.5px; color: #8b93a7; margin-top: 8px; line-height: 1.45; }

.sec-label    { font-size: 10px; font-weight: 700; letter-spacing: .14em;
                text-transform: uppercase; color: #8b9cf9; margin-bottom: 8px; }
.sec-title    { font-size: 23px; font-weight: 800; color: #f2f5fb;
                letter-spacing: -.5px; margin-bottom: 6px; line-height: 1.15; }
.sec-sub      { font-size: 12.5px; color: #8b93a7; margin-bottom: 18px;
                line-height: 1.6; max-width: 720px; }

.footer       { font-size: 11px; color: #5c6478; text-align: center;
                margin-top: 2.5rem; letter-spacing: .03em; }

hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 3.5rem 0; }

/* ── glassy sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(15,20,38,0.72);
    backdrop-filter: blur(24px) saturate(140%);
    -webkit-backdrop-filter: blur(24px) saturate(140%);
    border-right: 1px solid rgba(255,255,255,0.10);
}
[data-testid="stSidebar"] * { color: #e7ecf5; }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {
    color: #8b93a7 !important; }

/* ── mobile ── */
@media (max-width: 640px) {
    .block-container { padding-left: 1.1rem; padding-right: 1.1rem;
                       padding-top: 1.6rem; }
    .hero-title { font-size: 32px; letter-spacing: -1px; }
    .hero-sub   { font-size: 13px; }
    .sec-title  { font-size: 19px; }
    .sec-sub    { font-size: 12px; }
    .kpi        { padding: 12px 14px; }
    .kpi-value  { font-size: 23px; }
    hr { margin: 2.2rem 0; }
    [data-testid="stHorizontalBlock"] { gap: 0.4rem; }
}
</style>
""", unsafe_allow_html=True)
```

- [ ] **Step 3: Make KPI tiles glass cards**

In the KPI render loop, change the wrapper div class from `kpi{" accent"}` to `glass kpi{" accent"}`:

```python
    col.markdown(
        f'<div class="glass kpi{" accent" if accent else ""}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{val}</div>'
        f'<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )
```

- [ ] **Step 4: Update hero copy for live data**

Compute matches/rows from data instead of hardcoding:

```python
n_matches = df_all["match"].n_unique()
st.markdown(
    f'<div class="hero-sub">Every sprint measured by FIFA\'s physical '
    f'performance system. {n_matches} matches · '
    f'{df_all["team"].n_unique()} teams · {len(df_all):,} player appearances '
    f'— refreshed daily as new match reports publish.</div>',
    unsafe_allow_html=True,
)
```

- [ ] **Step 5: Visual verification**

Run: `uv run streamlit run app.py` and check in browser (desktop + ~390px width):
dark gradient visible, KPI tiles frosted, charts legible (gridlines subtle, labels readable), hover cards dark, sidebar glassy, no white flashes.
Fix any contrast issues found (this is the audit loop — iterate until clean).

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "Liquid glass redesign: dark gradient, frosted cards, retheme charts"
```

---

### Task 8: Bug audit, README refresh, final verification

**Files:**
- Modify: `app.py` (fixes found in audit), `README.md`

**Interfaces:**
- Consumes: the running app with 72-match data.
- Produces: clean audit, accurate README, all tests green.

- [ ] **Step 1: Guard KDE crash on degenerate teams**

In `ridgeline()`, a team whose speeds are all identical makes `gaussian_kde` raise (singular matrix). Wrap:

```python
        try:
            kde = gaussian_kde(sub, bw_method=0.35)
        except Exception:
            continue
```

- [ ] **Step 2: Interactive audit**

Run the app; exercise systematically, fixing anything broken as found:
- Filter to a single team; single match; a team+match combo with no rows (warning shows, no crash).
- Sliders at min/max (top N 40 with < 40 rows filtered — `head(n)` handles short data; verify).
- Dumbbell click-to-hide: hide rows, "Show all" button, then change a filter — hidden set resets (Task 6 fix).
- Leaderboard with < 3 rows (medal dict indexing is `.get`, verify no crash).
- Mobile width: charts fit, KPIs stack.

- [ ] **Step 3: Update README**

Regenerate the top-20 tables from `data/top_speeds.csv` (km/h and mph, mph = kmh / 1.609344, one decimal), update counts (72 matches, actual row count), replace `main.py` row in the Files table with `pipeline/` (Dagster assets) and add `infra/` (Terraform). Add a short "Pipeline" section:

```markdown
## Pipeline

Dagster + S3 (Terraform-provisioned, bucket `fifa-topspeed-<account>`):

- `uv run dagster dev` — UI with lineage, manual runs, daily schedule
- `uv run dagster asset materialize -m pipeline.definitions --select '*'` — one-shot refresh
- Assets: `match_report_urls` → `raw_match_pdfs` (incremental, append-only raw zone) → `top_speeds` (parquet in S3 + `data/top_speeds.csv` fallback)
- `terraform -chdir=infra apply` — provision the bucket
```

Keep the HF Spaces frontmatter block at the top intact.

- [ ] **Step 4: Full test suite + app smoke test**

Run: `uv run pytest tests/ -v` — all PASS.
Run the app once more end-to-end; confirm no console errors.

- [ ] **Step 5: Commit**

```bash
git add app.py README.md
git commit -m "Bug audit fixes; refresh README for 72-match data and pipeline docs"
```

---

## Self-review notes

- Spec coverage: Terraform bucket (T1), parsing+tests (T2), storage (T3), Dagster assets/schedule (T4), backfill+retire main.py (T5), S3 app loading+fallback (T6), liquid glass (T7), bug audit+README (T8). Error handling: per-PDF logging (T4), 0-row Failure (T4), validation drops (T2), app fallback (T6), KDE guard (T8). ✔
- Types consistent across tasks (`list[str]` keys, `list[dict]` rows, `tuple[list[dict], int]` validate). ✔
- No placeholders. ✔
