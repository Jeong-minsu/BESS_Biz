"""
Cross-check 2026 AS award/revenue across multiple PTP endpoints for 2026-03-15.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa
from fetch_pnl_data import tenaska_token, tenaska_query, flatten_query, PTP_BASE  # noqa

FLOWDAY = "2026-03-15"
ROOT = "ERCOTNodal"
GKS_ESR_UUID = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"


def list_elements(token, ep):
    url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(ep)}/elements"
    r = requests.get(url, params={"begin": FLOWDAY, "end": FLOWDAY},
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    try:
        data = r.json().get("data", [])
    except Exception:
        return []
    return data if isinstance(data, list) else []


def main():
    token = tenaska_token(load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {}))

    # Endpoints to test
    candidates = [
        "ERCOT_DA_Awards_Prices",
        "DA_Awards_Prices_All",
        "Day-Ahead-Settlement-Amounts",
        "Real-Time-Settlement-Amounts",
        "Settlement-Summary",
        "EnergySettlement",
        "Generator-Settlement-Data",
        "Day_Ahead_Daily_Settlement",
        "Real_Time_Daily_Settlement",
        "Battery-Settlement-Details",
        "DART-Energy-Details",
        "Configuration-Awards",
    ]

    for ep in candidates:
        print(f"\n{'='*72}\n  {ep}\n{'='*72}")
        elements = list_elements(token, ep)
        kg = [e for e in elements
               if isinstance(e, dict)
                   and ("iskadee" in str(e.get("name", "")).lower()
                        or "GKS" in str(e.get("name", "")).upper())]
        print(f"  total elements: {len(elements)}  GKS matches: {len(kg)}")
        for e in kg[:5]:
            print(f"    • name={e.get('name')!r:55s}  def={e.get('elementDefinition')!r:18s}  id={e.get('identifier','')[:36]}")
        # Try query (path=query, ByIdentifier with the ESR UUID) for AS-relevant ones
        if not kg:
            continue
        uuid = kg[0].get("identifier")
        if not uuid:
            continue
        try:
            j = tenaska_query(
                token, ROOT, ep,
                __import__("datetime").date.fromisoformat(FLOWDAY),
                "",  # filter
                datapoints=None,
                element_definition=kg[0].get("elementDefinition"),
                path="query",
                element_identifiers=[uuid],
            )
            rows = flatten_query(j)
            # Aggregate by datapoint
            agg = defaultdict(float)
            cnts = defaultdict(int)
            for r in rows:
                v = r.get("value")
                if isinstance(v, (int, float)):
                    agg[r["datapoint"]] += v
                    cnts[r["datapoint"]] += 1
            print(f"  rows: {len(rows)};  unique datapoints: {len(agg)}")
            # AS-relevant tokens
            for k in sorted(agg):
                kl = k.lower()
                if any(t in kl for t in ("ns_", "nspin", "rrs", "ecrs", "reg_up",
                                            "reg_down", "regup", "regdn",
                                            "ancillary", "as_", "award", "settle", "amt")):
                    print(f"    • {k:45s}  sum={agg[k]:>14,.2f}  n={cnts[k]}")
        except Exception as e:
            print(f"  query err: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
