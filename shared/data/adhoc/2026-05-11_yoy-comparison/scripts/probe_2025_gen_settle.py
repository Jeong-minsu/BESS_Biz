"""
Probe Generator-Settlement-Data for a 2025 flowday — find Kiskadee entities and
non-zero AS-related fields.
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

FLOWDAY = "2025-03-15"
ROOT = "ERCOTNodal"
EP = "Generator-Settlement-Data"


def main():
    token = tenaska_token(load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {}))
    hdrs = {"Authorization": f"Bearer {token}"}

    # elements
    r = requests.get(f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(EP)}/elements",
                     params={"begin": FLOWDAY, "end": FLOWDAY}, headers=hdrs, timeout=30)
    data = r.json().get("data", [])
    if not isinstance(data, list):
        print("non-list response"); return
    gks = [e for e in data
            if isinstance(e, dict) and "iskadee" in str(e.get("name", "")).lower()]
    print(f"2025 GenSettle elements: {len(data)} total, {len(gks)} GKS-matching:")
    for e in gks:
        print(f"   • name={e.get('name')!r:60s}  def={e.get('elementDefinition')!r}  id={e.get('identifier','')[:36]}")

    # Query each Kiskadee entity
    for e in gks:
        uuid = e.get("identifier")
        nm = e.get("name")
        eldef = e.get("elementDefinition")
        try:
            j = tenaska_query(token, ROOT, EP, date.fromisoformat(FLOWDAY),
                              "", datapoints=None,
                              element_definition=eldef,
                              path="query",
                              element_identifiers=[uuid])
            rows = flatten_query(j)
            agg, cnts = defaultdict(float), defaultdict(int)
            for r in rows:
                v = r.get("value")
                if isinstance(v, (int, float)):
                    agg[r["datapoint"]] += v
                    cnts[r["datapoint"]] += 1
            print(f"\n[{nm}]  rows={len(rows)}  uniq datapoints={len(agg)}")
            for k in sorted(agg):
                if abs(agg[k]) > 0.01:
                    print(f"   • {k:35s}  sum={agg[k]:>14,.2f}  n={cnts[k]}")
        except Exception as ex:
            print(f"[{nm}] err: {ex}")


if __name__ == "__main__":
    main()
