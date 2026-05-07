"""
List actual elements (resource instances) for each viewport so we know what
'Name contains X' filter to use.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections  # noqa
from fetch_pnl_data import tenaska_token, PTP_BASE  # noqa

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
ROOT = "ERCOTNodal"
FLOWDAY = "2026-05-03"

ENDPOINTS = [
    ("Battery-Settlement-Details", None),
    ("Generator-Performance", None),
    ("Submissions-DA-Energy-Bid", None),
    ("Submissions-DA-Energy-Only-Offer", None),
]

def main() -> None:
    sections = load_env_sections(ENV_PATH)
    token = tenaska_token(sections.get("tenaska", {}))
    hdrs = {"Authorization": f"Bearer {token}"}

    for endpoint, eldef in ENDPOINTS:
        print(f"\n{'='*72}\n{endpoint}  (elementDefinition={eldef!r})\n{'='*72}")
        url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(endpoint)}/elements"
        params = {"begin": FLOWDAY, "end": FLOWDAY}
        if eldef:
            params["elementDefinition"] = eldef
        try:
            r = requests.get(url, params=params, headers=hdrs, timeout=30)
            if r.status_code >= 400:
                print(f"   ❌ {r.status_code}: {r.text[:300]}")
                continue
            j = r.json()
        except Exception as e:
            print(f"   ❌ {type(e).__name__}: {e}")
            continue

        data = j.get("data", j)
        if isinstance(data, list):
            print(f"   {len(data)} elements")
            # show ones with GKS in name first, then sample
            gks = [e for e in data if "GKS" in str(e).upper() or (isinstance(e, dict) and "GKS" in str(e.get("name","")).upper())]
            print(f"   GKS-matching: {len(gks)}")
            for e in gks[:20]:
                if isinstance(e, dict):
                    print(f"     • name={e.get('name')!r}  def={e.get('elementDefinition')!r}  id={str(e.get('identifier',''))[:36]}")
                else:
                    print(f"     • {e!r}")
            if not gks and data:
                print("   (sample of first 5)")
                for e in data[:5]:
                    if isinstance(e, dict):
                        print(f"     • name={e.get('name')!r}  def={e.get('elementDefinition')!r}")
                    else:
                        print(f"     • {e!r}")
        elif isinstance(data, dict):
            print(f"   dict keys: {list(data.keys())}")
            for k, v in list(data.items())[:6]:
                print(f"     {k}: {str(v)[:200]}")

if __name__ == "__main__":
    main()
