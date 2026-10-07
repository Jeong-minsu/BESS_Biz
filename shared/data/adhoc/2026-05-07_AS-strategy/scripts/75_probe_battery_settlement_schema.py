"""
Probe #75 — full datapoint schema of Battery-Settlement-Details (Energy & AS Detail).

The default `dataPoints=None` pull returned only 18 datapoints (no per-product RT AS
revenue). Check the viewport SCHEMA for the complete datapoint list, then do an
explicit query for any RT AS revenue datapoints found.
"""
from __future__ import annotations
import base64, json, sys, urllib.parse
from datetime import date
from pathlib import Path
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections, first  # noqa
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://api.ptp.energy"
ROOT = "ERCOTNodal"
EP = "Battery-Settlement-Details"
GKS_ESR_UUID = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"
OUT = Path(__file__).resolve().parents[1] / "raw" / "battery_settlement_schema.json"


def tok(tk):
    u, p = first(tk, "TENASKA_USERNAME", "USERNAME"), first(tk, "TENASKA_PASSWORD", "PASSWORD")
    b = base64.b64encode(f"{u}:{p}".encode()).decode()
    r = requests.get(f"{BASE}/authentication/token",
                     headers={"Authorization": f"Basic {b}"}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def main():
    tk = load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {})
    H = {"Authorization": f"Bearer {tok(tk)}", "Content-Type": "application/json"}

    # 1. schema
    r = requests.get(f"{BASE}/ptp/{ROOT}/{urllib.parse.quote(EP)}", headers=H, timeout=30)
    print("schema status:", r.status_code)
    j = r.json()
    OUT.write_text(json.dumps(j, indent=1, default=str), encoding="utf-8")
    data = j.get("data", j)
    # datapoints may be under several keys
    dps = data.get("dataPoints") or data.get("DataPoints") or []
    names = sorted((d.get("keyName") or d.get("name") or d) if isinstance(d, dict) else d
                   for d in dps)
    print(f"\nTotal schema datapoints: {len(names)}")
    for n in names:
        print("  ", n)
    rt_as = [n for n in names if "RT" in str(n).upper()
             and any(k in str(n).upper() for k in ("NS", "RRS", "ECR", "REG", "AS", "ANC"))]
    print(f"\nRT AS-looking datapoints: {rt_as}")

    # 2. explicit query for ALL schema datapoints on a sample flowday
    if names:
        payload = {"begin": "2026-05-09", "end": "2026-05-09",
                   "elementQueryMode": "ByIdentifier",
                   "elementIdentifiers": [GKS_ESR_UUID],
                   "sequenceOptions": "GreatestEnabled",
                   "dataPoints": list(names)}
        r2 = requests.post(f"{BASE}/ptp/{ROOT}/{urllib.parse.quote(EP)}/query",
                           json=payload, headers=H, timeout=120)
        print("\nexplicit-all query status:", r2.status_code)
        jj = r2.json()
        seen = {}
        for el in jj.get("data", []) or []:
            for dp in el.get("dataPoints", []) or []:
                vals = [d.get("value") for v in dp.get("values", []) for d in v.get("data", [])]
                nz = [x for x in vals if isinstance(x, (int, float)) and x != 0]
                seen[dp.get("keyName")] = {"n": len(vals), "nonzero": len(nz),
                                           "sample": (nz[:3] or vals[:3])}
        print("returned datapoints:")
        for k in sorted(seen):
            v = seen[k]
            print(f"  {k:32s} n={v['n']:3d} nonzero={v['nonzero']:3d} sample={v['sample']}")
        for vv in jj.get("validations", []):
            print(f"  validation [{vv.get('severity')} {vv.get('code')}]: {vv.get('message')}")


if __name__ == "__main__":
    main()
