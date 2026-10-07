"""
DART regime analysis #02 — Tenaska energy_as_detail backfill, 2026-07-01 .. 2026-08-23.

Caches per-day JSON into shared/data/pnl/gks/hourly/ (same convention as
virtual_exposure_2026.py — skips days already cached).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from fetch_pnl_data import (  # noqa: E402
    ENV_PATH, PNL_DIR,
    tenaska_token, discover_tenaska_endpoints, tenaska_query, flatten_query,
)
from _env_loader import load_env_sections  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

START = date(2026, 7, 1)
END = date(2026, 8, 23)
GKS_ESR_UUID = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"


def main() -> None:
    sections = load_env_sections(ENV_PATH)
    tk = sections.get("tenaska", {})
    eps = discover_tenaska_endpoints(tk)
    token = tenaska_token(tk)
    root, ep = eps["root"], eps["energy_as_detail"]

    d = START
    n_ok = n_cached = n_fail = 0
    while d <= END:
        cached = PNL_DIR / f"{d.isoformat()}_energy_as_detail.json"
        if cached.exists():
            n_cached += 1
            d += timedelta(days=1)
            continue
        try:
            j = tenaska_query(
                token, root, ep, d,
                resource_filter="",
                datapoints=None,
                element_definition="Entity",
                path="query",
                element_identifiers=[GKS_ESR_UUID],
            )
            rows = flatten_query(j)
            cached.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
            n_ok += 1
            print(f"  {d} OK rows={len(rows)}")
        except Exception as e:
            n_fail += 1
            print(f"  {d} FAIL {type(e).__name__}: {e}")
        time.sleep(1.1)
        d += timedelta(days=1)

    print(f"done: fetched={n_ok} cached={n_cached} failed={n_fail}")


if __name__ == "__main__":
    main()
