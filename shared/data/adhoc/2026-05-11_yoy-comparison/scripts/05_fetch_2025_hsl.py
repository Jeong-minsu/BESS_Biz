"""
YoY comparison #05 — Fetch 2025 GKS HSL/LSL from Tenaska PTP Generator-Performance.

Element: 'Great Kiskadee BESS'   UUID=565ab4f2-af92-462a-8f86-c8efd3d0a986
Endpoint: ERCOTNodal/Generator-Performance/query-columnar

Output: shared/data/pnl/gks/hourly/<date>_hsl.json   (per day)
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
GKS_BESS_UUID = "565ab4f2-af92-462a-8f86-c8efd3d0a986"


def daterange(s, e):
    d = s
    while d <= e:
        yield d
        d += timedelta(days=1)


def main():
    sections = load_env_sections(PROJECT_ROOT / ".env")
    endpoints = json.loads(ENDPOINT_CACHE.read_text())
    root = endpoints["root"]
    ep   = endpoints["hsl"]            # "Generator-Performance"
    token = tenaska_token(sections.get("tenaska", {}))
    PNL_DIR.mkdir(parents=True, exist_ok=True)

    days = list(daterange(START, END))
    print(f"[05_fetch_2025_hsl] {START}..{END} ({len(days)} days)")
    print(f"   endpoint: {root}/{ep}   UUID: {GKS_BESS_UUID[:8]}...")

    fail = []
    for i, d in enumerate(days, 1):
        out = PNL_DIR / f"{d.isoformat()}_hsl.json"
        if out.exists() and out.stat().st_size > 1000:
            print(f"[{i}/{len(days)}] {d} SKIP")
            continue
        print(f"[{i}/{len(days)}] {d}", end=" ... ", flush=True)
        try:
            j = tenaska_query(token, root, ep, d, "",
                              datapoints=["Telemetered_HSL_5_Min",
                                          "Telemetered_LSL_5_Min",
                                          "Telemetered_Generation_15_Min"],
                              element_definition="Generator",
                              path="query-columnar",
                              element_identifiers=[GKS_BESS_UUID])
            rows = flatten_query(j)
            out.write_text(json.dumps(rows, indent=2, default=str),
                            encoding="utf-8")
            print(f"{len(rows)} rows")
        except Exception as e:
            print(f"ERR: {type(e).__name__}: {e}")
            fail.append(d)
            time.sleep(2)
        time.sleep(0.3)

    print(f"\n===== DONE =====")
    print(f"  success: {len(days) - len(fail)} / {len(days)}")
    if fail:
        print(f"  failed: {[d.isoformat() for d in fail]}")


if __name__ == "__main__":
    main()
