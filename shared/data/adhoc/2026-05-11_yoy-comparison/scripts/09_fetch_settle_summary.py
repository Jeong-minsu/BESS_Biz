"""
YoY comparison #09 — Fetch Settlement-Summary for both years (Feb14..Apr30)
to verify total revenue figures against the most authoritative ERCOT
statement-style endpoint.

Saves to shared/data/pnl/gks/hourly/<date>_settle_summary.json
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa
from fetch_pnl_data import tenaska_token, tenaska_query, flatten_query  # noqa

PNL_DIR = PROJECT_ROOT / "shared" / "data" / "pnl" / "gks" / "hourly"
ROOT = "ERCOTNodal"
EP = "Settlement-Summary"

# Use the Gen Resource UUID for pre-RTC, ESR UUID for post-RTC
GEN_UUID_2025 = "549e9554-a78b-4c02-8f16-d59270953e82"  # 'Great Kiskadee Storage, LLC Gen'
ESR_UUID_2026 = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"  # 'Great Kiskadee Storage - ESR'


def daterange(s, e):
    d = s
    while d <= e:
        yield d
        d += timedelta(days=1)


def fetch_year(year: int, uuid: str):
    sections = load_env_sections(PROJECT_ROOT / ".env")
    token = tenaska_token(sections.get("tenaska", {}))
    PNL_DIR.mkdir(parents=True, exist_ok=True)

    start = date(year, 2, 14)
    end   = date(year, 4, 30)
    days = list(daterange(start, end))
    print(f"\n[Settlement-Summary {year}] {start}..{end} ({len(days)} days)  UUID={uuid[:8]}...")
    fail = []
    for i, d in enumerate(days, 1):
        out = PNL_DIR / f"{d.isoformat()}_settle_summary.json"
        if out.exists() and out.stat().st_size > 200:
            continue
        print(f"  [{i}/{len(days)}] {d}", end=" ... ", flush=True)
        try:
            j = tenaska_query(token, ROOT, EP, d, "",
                              datapoints=None,
                              element_definition=None,
                              path="query",
                              element_identifiers=[uuid])
            rows = flatten_query(j)
            out.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
            print(f"{len(rows)} rows")
        except Exception as e:
            print(f"ERR: {e}")
            fail.append(d)
            time.sleep(2)
        time.sleep(0.3)
    print(f"  done: {len(days)-len(fail)}/{len(days)}")


def main():
    fetch_year(2025, GEN_UUID_2025)
    fetch_year(2026, ESR_UUID_2026)


if __name__ == "__main__":
    main()
