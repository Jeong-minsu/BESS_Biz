"""
List all Tenaska PTP viewports that could carry AS settlement/award data for 2026,
to cross-check whether DA_NS_Amt in Battery-Settlement-Details matches an authoritative source.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections  # noqa
from fetch_pnl_data import tenaska_token, PTP_BASE  # noqa

ROOT = "ERCOTNodal"
FLOWDAY = "2026-03-15"


def main():
    token = tenaska_token(load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {}))
    hdrs = {"Authorization": f"Bearer {token}"}

    # 1. List all available viewports
    print("="*70, "\nALL VIEWPORTS available under ERCOTNodal\n", "="*70, sep="")
    r = requests.get(f"{PTP_BASE}/ptp/{ROOT}", headers=hdrs, timeout=30)
    vps_raw = r.json().get("data", [])
    # Could be list of dicts or list of strings — normalize
    vps = []
    for v in vps_raw:
        if isinstance(v, dict):
            vps.append(v.get("name", ""))
        else:
            vps.append(str(v))
    print(f"Total viewports: {len(vps)}")
    print("All viewports:")
    for v in vps:
        print(f"  • {v!r}")
    print()
    candidates = []
    for name in vps:
        nlow = name.lower()
        if any(k in nlow for k in ("as ", "ancillary", "nspin", "non-spin", "rrs", "ecrs",
                                     "regulation", "reg-up", "reg-dn", "award", "mcpc",
                                     "settlement", "deployment")):
            candidates.append(name)
    candidates.sort()
    print(f"\nAS / settlement / deployment candidates ({len(candidates)}):")
    for c in candidates:
        print(f"   • {c!r}")

    # 2. For each candidate, list elements and try a sample query
    interesting = [c for c in candidates
                    if "Settlement" in c or "Award" in c or "AS-" in c
                       or "Ancillary" in c]
    print(f"\n\n{'='*70}\nELEMENTS in top picks (2026-03-15)\n{'='*70}")
    for vp in interesting:
        url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(vp)}/elements"
        try:
            r = requests.get(url, params={"begin": FLOWDAY, "end": FLOWDAY},
                             headers=hdrs, timeout=30)
            if r.status_code >= 400:
                print(f"\n[{vp}] HTTP {r.status_code}: {r.text[:200]}")
                continue
            data = r.json().get("data", [])
            if not isinstance(data, list):
                print(f"\n[{vp}] non-list response")
                continue
            kg = [e for e in data
                   if isinstance(e, dict)
                       and ("iskadee" in str(e.get("name", "")).lower()
                            or "GKS" in str(e.get("name", "")).upper())]
            print(f"\n[{vp}]  total={len(data)}  GKS={len(kg)}")
            for e in kg:
                print(f"    • name={e.get('name')!r:60s}  def={e.get('elementDefinition')!r}  id={e.get('identifier','')[:36]}")
        except Exception as e:
            print(f"\n[{vp}] ERR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
