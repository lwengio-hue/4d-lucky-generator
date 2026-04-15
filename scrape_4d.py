"""
SG Pools 4D Results Scraper
============================
Fetches ALL available 4D draw results from Singapore Pools and saves to SQLite.

Data availability (confirmed by live testing, Apr 2026):
  - Draws 1–9      : AVAILABLE (Jun 1986)
  - Draws 10–999   : MISSING   (server-side gap — not hosted)
  - Draws 1000–5469: AVAILABLE (Dec 1995 → Apr 2026)
  Total: ~4,479 draws with data  |  ~990 draws in gap (unavailable)

Schema: 4d_results.db → table `draws`
  draw_number        INTEGER PRIMARY KEY
  draw_date          TEXT
  first_prize        TEXT
  second_prize       TEXT
  third_prize        TEXT
  starter_1..10      TEXT   (10 starter prize numbers)
  consolation_1..10  TEXT   (10 consolation prize numbers)
  scraped_at         TEXT
"""

from __future__ import annotations
import requests
import base64
import sqlite3
import time
import re
import os
from datetime import datetime
from bs4 import BeautifulSoup
os.makedirs("data", exist_ok=True)

# ── Configuration ────────────────────────────────────────────────────────────
DB_PATH = "data/4d_results.db"
DELAY_SEC     = 1.5
TIMEOUT_SEC   = 20
MAX_RETRIES   = 3
BASE_URL      = "https://www.singaporepools.com.sg/en/product/Pages/4d_results.aspx"
DRAW_LIST_URL = "https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/fourd_result_draw_list_en.html"

# Draw ranges to attempt (draws 10–999 are confirmed missing on server)
# Range 1: draws 1–9 (Jun 1986 originals)
# Range 2: draws 1000–latest
RANGE_1_START = 1
RANGE_1_END   = 9
RANGE_2_START = 1000
RANGE_2_END   = None   # None = auto-detect latest
# ─────────────────────────────────────────────────────────────────────────────


def encode_draw(n: int) -> str:
    """Encode draw number to base64 query string."""
    raw = f"DrawNumber={n}".encode()
    return base64.b64encode(raw).decode().rstrip("=")


def get_latest_draw_number() -> int:
    """Scrape the draw list page to find the highest draw number."""
    print("  Fetching latest draw number from SG Pools …")
    r = requests.get(DRAW_LIST_URL, timeout=TIMEOUT_SEC)
    r.raise_for_status()
    matches = re.findall(r"value='(\d+)'", r.text)
    if not matches:
        raise RuntimeError("Could not find any draw numbers in draw list page.")
    latest = max(int(m) for m in matches)
    print(f"  Latest 4D draw found: {latest}")
    return latest


def init_db(conn: sqlite3.Connection):
    """Create the draws table if it doesn't exist."""
    # Build column definitions for 10 starters and 10 consolations
    starter_cols    = "\n".join(f"    starter_{i:<2}    TEXT," for i in range(1, 11))
    consolation_cols= "\n".join(f"    consolation_{i:<2} TEXT," for i in range(1, 11))

    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS draws (
            draw_number    INTEGER PRIMARY KEY,
            draw_date      TEXT,
            first_prize    TEXT,
            second_prize   TEXT,
            third_prize    TEXT,
{starter_cols}
{consolation_cols}
            scraped_at     TEXT
        )
    """)
    conn.commit()


def get_existing_draws(conn: sqlite3.Connection) -> tuple[set, set]:
    """
    Returns two sets:
      complete : draw numbers fully valid (skip these)
      corrupt  : draw numbers with null prizes (re-scrape these)

    Corrupt = first_prize OR second_prize OR third_prize is NULL
    """
    cur = conn.execute("""
        SELECT draw_number, first_prize, second_prize, third_prize
        FROM draws
    """)
    complete = set()
    corrupt  = set()
    for row in cur.fetchall():
        draw_num    = row[0]
        has_null    = any(v is None for v in row[1:4])

        if has_null:
            corrupt.add(draw_num)
        else:
            complete.add(draw_num)

    return complete, corrupt


def fetch_draw(draw_num: int, session: requests.Session) -> dict | None:
    """
    Fetch and parse a single 4D draw.
    Returns a dict of fields, or None if the draw is not available.
    """
    qs  = encode_draw(draw_num)
    url = f"{BASE_URL}?sppl={qs}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=TIMEOUT_SEC)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                print(f"\n    [ERROR] Draw {draw_num} failed after {MAX_RETRIES} retries: {e}")
                return None
            time.sleep(3)

    soup = BeautifulSoup(r.text, "html.parser")

    # ── Detect unavailable draw ──────────────────────────────────────────────
    draw_num_el = soup.find(class_="drawNumber")
    if not draw_num_el:
        return None
    returned_match = re.search(r"\d+", draw_num_el.text)
    if not returned_match:
        return None
    returned_num = int(returned_match.group())
    if returned_num != draw_num:
        return None  # Server returned a different draw

    # ── Date ────────────────────────────────────────────────────────────────
    draw_date_el = soup.find(class_="drawDate")
    draw_date    = draw_date_el.text.strip() if draw_date_el else "Unknown"

    # ── Prizes ───────────────────────────────────────────────────────────────
    first  = soup.find(class_="tdFirstPrize")
    second = soup.find(class_="tdSecondPrize")
    third  = soup.find(class_="tdThirdPrize")

    first_prize  = first.text.strip()  if first  else None
    second_prize = second.text.strip() if second else None
    third_prize  = third.text.strip()  if third  else None

    # ── Starter prizes (10 numbers) ──────────────────────────────────────────
    starters_body = soup.find(class_="tbodyStarterPrizes")
    starter_nums  = []
    if starters_body:
        starter_nums = [td.text.strip() for td in starters_body.find_all("td")]
    # Pad to exactly 10
    starter_nums = (starter_nums + [None] * 10)[:10]

    # ── Consolation prizes (10 numbers) ─────────────────────────────────────
    consols_body  = soup.find(class_="tbodyConsolationPrizes")
    consol_nums   = []
    if consols_body:
        consol_nums = [td.text.strip() for td in consols_body.find_all("td")]
    consol_nums = (consol_nums + [None] * 10)[:10]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "draw_number" : draw_num,
        "draw_date"   : draw_date,
        "first_prize" : first_prize,
        "second_prize": second_prize,
        "third_prize" : third_prize,
        "scraped_at"  : now,
    }
    for i, val in enumerate(starter_nums, start=1):
        row[f"starter_{i}"] = val
    for i, val in enumerate(consol_nums, start=1):
        row[f"consolation_{i}"] = val

    return row


def insert_draw(conn: sqlite3.Connection, data: dict):
    # Build dynamic INSERT for variable column names
    cols      = list(data.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    col_names    = ", ".join(cols)
    conn.execute(
        f"INSERT OR REPLACE INTO draws ({col_names}) VALUES ({placeholders})",
        data
    )
    conn.commit()


def progress_bar(current: int, total: int, width: int = 50) -> str:
    filled = int(width * current / total) if total > 0 else 0
    bar    = "█" * filled + "░" * (width - filled)
    pct    = 100 * current / total if total > 0 else 0
    return f"[{bar}] {pct:5.1f}% ({current}/{total})"


def main():
    print("=" * 65)
    print("  SG POOLS — 4D RESULTS SCRAPER")
    print("=" * 65)

    # ── Determine draw ranges ────────────────────────────────────────────────
    range_2_end  = RANGE_2_END or get_latest_draw_number()
    draws_range1 = list(range(RANGE_1_START, RANGE_1_END + 1))
    draws_range2 = list(range(RANGE_2_START, range_2_end + 1))
    draws_all    = draws_range1 + draws_range2
    total        = len(draws_all)

    print(f"\n  Draw ranges  : {RANGE_1_START}–{RANGE_1_END} (early 1986)")
    print(f"               + {RANGE_2_START}–{range_2_end} (Dec 1995 → now)")
    print(f"  Total attempts: {total:,} draws")
    print(f"  NOTE: Draws 10–999 are skipped (confirmed missing on server)")
    print(f"  Output DB    : {DB_PATH}")
    print(f"  Delay        : {DELAY_SEC}s between requests\n")

    # ── Init DB ──────────────────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    complete, corrupt = get_existing_draws(conn)
    print(f"  Already in DB : {len(complete):,} complete draws (will skip)")
    print(f"  Corrupt rows  : {len(corrupt):,} draws flagged for re-scrape")

    # ── Scrape loop ──────────────────────────────────────────────────────────
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    })

    saved     = 0
    skipped   = 0
    missing   = 0
    processed = 0
    start_time = time.time()

    for draw_num in draws_all:
        processed += 1

         # Skip already-scraped draws
        if draw_num in complete:
            skipped += 1
            continue
        if draw_num in corrupt:
            print(f"\n  ♻️  Re-scraping corrupt draw #{draw_num}...")

        if processed % 10 == 0 or processed == 1:
            elapsed  = time.time() - start_time
            rate     = (processed - skipped) / elapsed if elapsed > 0 else 0
            eta_secs = (total - processed) / rate if rate > 0 else 0
            eta_str  = f"{int(eta_secs//60)}m {int(eta_secs%60)}s"
            bar      = progress_bar(processed, total)
            print(f"\r  {bar}  |  saved:{saved:,}  missing:{missing:,}  ETA:{eta_str}   ", end="", flush=True)

        data = fetch_draw(draw_num, session)

        if data is None:
            missing += 1
        else:
            insert_draw(conn, data)
            saved += 1

        time.sleep(DELAY_SEC)

    # ── Final summary ────────────────────────────────────────────────────────
    conn.close()
    elapsed = time.time() - start_time
    print(f"\n\n{'=' * 65}")
    print(f"  4D SCRAPE COMPLETE")
    print(f"{'=' * 65}")
    print(f"  Draws saved       : {saved:,}")
    print(f"  Draws skipped     : {skipped:,}  (already in DB)")
    print(f"  Draws not found   : {missing:,}  (not on server)")
    print(f"  Time taken        : {int(elapsed//60)}m {int(elapsed%60)}s")
    print(f"  Output file       : {DB_PATH}")
    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
