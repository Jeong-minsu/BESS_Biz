"""
Probe Settlement-Summary and EnergySettlement for 2025-03-15 to cross-check
total revenue figures.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from collections import defaultdict
from datetime import date
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa
from fetch_pnl_data import tenaska_token, tenaska_query, flatten_query, PTP_BASE  # noqa

ROOT = "ERCOTNodal"
FLOWDAY = "2025-03-15"

EPS = ["Settlement-Summary", "EnergySettlement",
        "Day_Ahead_Daily_Settlement", "Real_Time_Daily_Settlement",
        "Day-Ahead-Settlement-Amounts", "Real-Time-Settlement-Amounts",
        "ERCOT-Statement-Values", "Settlement-Charges", "Market-Settlement-Values",
        "DART-Energy-Details"]


def main():
    token = tenaska_token(load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {}))
    hdrs = {"Authorization": f"Bearer {token}"}

    for ep in EPS:
        print(f"\n{'='*72}\n  {ep}\n{'='*72}")
        # Elements
        url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(ep)}/elements"
        try:
            r = requests.get(url, params={"begin": FLOWDAY, "end": FLOWDAY},
                             headers=hdrs, timeout=30)
            if r.status_code >= 400:
                print(f"   elements HTTP {r.status_code}")
                continue
            data = r.json().get("data", [])
            if not isinstance(data, list):
                continue
            gks = [e for e in data
                    if isinstance(e, dict)
                        and "iskadee" in str(e.get("name", "")).lower()]
            print(f"  total={len(data)}  GKS={len(gks)}")
            for e in gks[:4]:
                print(f"   • {e.get('name')!r:55s}  id={e.get('identifier','')[:36]}")
            if not gks:
                continue
            # Query each Kiskadee element
            for el in gks:
                uuid = el.get("identifier")
                nm = el.get("name")
                eldef = el.get("elementDefinition")
                try:
                    j = tenaska_query(token, ROOT, ep, date.fromisoformat(FLOWDAY),
                                      "", datapoints=None, element_definition=eldef,
                                      path="query", element_identifiers=[uuid])
                    rows = flatten_query(j)
                    agg = defaultdict(float)
                    for r in rows:
                        v = r.get("value")
                        if isinstance(v, (int, float)):
                            agg[r["datapoint"]] += v
                    if agg:
                        print(f"   [{nm}] non-zero ({len([k for k in agg if abs(agg[k])>0.01])}):")
                        for k, v in sorted(agg.items()):
                            if abs(v) > 0.01:
                                print(f"     • {k:25s}  {v:>14,.2f}")
                except Exception as ex:
                    print(f"   [{nm}] err {ex}")
        except Exception as e:
            print(f"  ERR {e}")


if __name__ == "__main__":
    main()
