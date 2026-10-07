"""
Probe Generator-Performance for 2025 — figure out why /query-columnar gives 500.
Try multiple path/def/identifier combos for a single 2025 flowday.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from datetime import date
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa
from fetch_pnl_data import tenaska_token, PTP_BASE  # noqa

ROOT = "ERCOTNodal"
EP = "Generator-Performance"
FLOWDAY = "2025-03-15"
UUID = "565ab4f2-af92-462a-8f86-c8efd3d0a986"


def call(token, payload, path):
    url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(EP)}/{path}"
    r = requests.post(url, json=payload,
                       headers={"Authorization": f"Bearer {token}",
                                "Content-Type": "application/json"},
                       timeout=60)
    return r.status_code, r.text[:300], (r.json() if r.status_code == 200 else None)


def main():
    token = tenaska_token(load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {}))

    base_payload = {
        "begin": f"{FLOWDAY}T00:00:00-06:00",
        "end":   f"{FLOWDAY}T23:59:59-06:00",
    }
    combos = [
        # (label, payload-override, path)
        ("query-columnar + UUID",
         {"elementQueryMode": "ByIdentifier", "elementIdentifiers": [UUID]},
         "query-columnar"),
        ("query + UUID",
         {"elementQueryMode": "ByIdentifier", "elementIdentifiers": [UUID]},
         "query"),
        ("query-columnar + filter=Kiskadee Generator",
         {"elementQueryMode": "ByParentAndFilter",
          "elementFilter": [{"elementProperty": "Name",
                              "expression": "contains 'Kiskadee'",
                              "elementDefinition": "Generator"}]},
         "query-columnar"),
        ("query + filter=Kiskadee Generator",
         {"elementQueryMode": "ByParentAndFilter",
          "elementFilter": [{"elementProperty": "Name",
                              "expression": "contains 'Kiskadee'",
                              "elementDefinition": "Generator"}]},
         "query"),
        ("query-columnar + UUID, datapoints=[Telemetered_HSL_5_Min]",
         {"elementQueryMode": "ByIdentifier",
          "elementIdentifiers": [UUID],
          "dataPoints": ["Telemetered_HSL_5_Min"]},
         "query-columnar"),
    ]
    for label, extra, path in combos:
        payload = {**base_payload, **extra}
        sc, body, j = call(token, payload, path)
        print(f"\n[{label}] path={path}")
        print(f"  HTTP {sc}; body[:200]: {body[:200]!r}")
        if j:
            data = j.get("data", j)
            if isinstance(data, list):
                print(f"  rows: {len(data)}")
            elif isinstance(data, dict):
                el = data.get("Elements", [])
                print(f"  Elements: {len(el)}")
                if el:
                    e0 = el[0]
                    dps = (e0.get("DataPoints") or {})
                    print(f"    sample element: name={e0.get('ElementName')}, datapoints={list(dps.keys())[:6]}")


if __name__ == "__main__":
    main()
