"""
YoY comparison #04 — Re-fetch 2025 GKS PTP using pre-RTC Gen + LR UUIDs.

Pre-RTC era: GKS settles as TWO Battery-Settlement-Details entities:
  • Gen Resource:  'Great Kiskadee Storage, LLC Gen'    id=549e9554-a78b-4c02-8f16-d59270953e82
  • Load Resource: 'Great Kiskadee Storage, LLC'        id=f9a55999-1c11-408d-902f-3f5fcb2776df

Output: shared/data/pnl/gks/hourly/<date>_energy_as_detail_v2.json   (per day)
  — each record has element name preserved so downstream can split Gen vs LR.

Skips dates already fetched (file present and non-trivial).
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
ENDPOINT_CACHE = (PROJECT_ROOT / "shared" / "scripts" / ".cache"
                   / "tenaska_endpoints.json")

START = date(2025, 2, 14)
END   = date(2025, 4, 30)
GEN_UUID = "549e9554-a78b-4c02-8f16-d59270953e82"
LR_UUID  = "f9a55999-1c11-408d-902f-3f5fcb2776df"


def daterange(s, e):
    d = s
    while d <= e:
        yield d
        d += timedelta(days=1)


def main():
    sections = load_env_sections(PROJECT_ROOT / ".env")
    endpoints = json.loads(ENDPOINT_CACHE.read_text())
    root = endpoints["root"]
    ep   = endpoints["energy_as_detail"]
    token = tenaska_token(sections.get("tenaska", {}))
    PNL_DIR.mkdir(parents=True, exist_ok=True)

    days = list(daterange(START, END))
    print(f"[04_fetch_2025_ptp_v2] {START}..{END}  ({len(days)} days)")
    print(f"   endpoint: {root}/{ep}   path=query")
    print(f"   UUIDs: Gen={GEN_UUID[:8]}... LR={LR_UUID[:8]}...")

    fail = []
    for i, d in enumerate(days, 1):
        out = PNL_DIR / f"{d.isoformat()}_energy_as_detail_v2.json"
        if out.exists() and out.stat().st_size > 1000:
            print(f"[{i}/{len(days)}] {d}  SKIP (exists)")
            continue
        print(f"[{i}/{len(days)}] {d}", end=" ... ", flush=True)
        try:
            j = tenaska_query(token, root, ep, d, "",
                              datapoints=None,
                              element_definition="Entity",
                              path="query",
                              element_identifiers=[GEN_UUID, LR_UUID])
            rows = flatten_query(j)
            out.write_text(json.dumps(rows, indent=2, default=str),
                            encoding="utf-8")
            print(f"{len(rows)} rows")
        except Exception as e:
            print(f"ERR: {type(e).__name__}: {e}")
            fail.append(d)
            time.sleep(2)
        time.sleep(0.5)

    print(f"\n===== DONE =====")
    print(f"  success: {len(days) - len(fail)} / {len(days)}")
    if fail:
        print(f"  failed: {[d.isoformat() for d in fail]}")


if __name__ == "__main__":
    main()
