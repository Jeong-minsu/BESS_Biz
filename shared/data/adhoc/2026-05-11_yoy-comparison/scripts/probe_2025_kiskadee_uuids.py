"""
Find Kiskadee pre-RTC Gen + LR UUIDs by probing Tenaska PTP elements for a 2025 flowday.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa
from fetch_pnl_data import tenaska_token, PTP_BASE  # noqa

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = "ERCOTNodal"
FLOWDAY = "2025-03-15"  # mid-period, should be representative
ENDPOINTS = [
    "Battery-Settlement-Details",
    "Generator-Performance",
    "Submissions-DA-Energy-Bid",
    "Submissions-DA-Energy-Only-Offer",
    "Generator-Resource-Output",
    "Load-Resource-Output",
]


def main():
    sections = load_env_sections(PROJECT_ROOT / ".env")
    token = tenaska_token(sections.get("tenaska", {}))
    hdrs = {"Authorization": f"Bearer {token}"}

    for endpoint in ENDPOINTS:
        print(f"\n{'='*72}\n{endpoint}\n{'='*72}")
        url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(endpoint)}/elements"
        params = {"begin": FLOWDAY, "end": FLOWDAY}
        try:
            r = requests.get(url, params=params, headers=hdrs, timeout=30)
            if r.status_code >= 400:
                print(f"  HTTP {r.status_code}: {r.text[:300]}")
                continue
            j = r.json()
        except Exception as e:
            print(f"  ERR: {type(e).__name__}: {e}")
            continue

        data = j.get("data", j)
        if isinstance(data, list):
            kg = [e for e in data
                   if isinstance(e, dict)
                       and "iskadee" in str(e.get("name", "")).lower()]
            if not kg:
                kg = [e for e in data
                       if isinstance(e, dict)
                           and "GKS" in str(e.get("name", "")).upper()]
            print(f"  total elements: {len(data)};  kiskadee/GKS matches: {len(kg)}")
            for e in kg:
                print(f"   • name={e.get('name')!r:60s}  def={e.get('elementDefinition')!r:18s}  id={e.get('identifier','')[:36]}")


if __name__ == "__main__":
    main()
