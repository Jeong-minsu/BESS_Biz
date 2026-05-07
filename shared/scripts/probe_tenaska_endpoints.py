"""
Probe candidate Tenaska PTP endpoints to find the right viewport for:
  energy_as_detail — DA + RT energy + AS (RegUp/RegDown/RRS/NonSpin/ECRS) revenue
                     + charging/discharging MW per HE
  da_energy_bid    — DA energy bid clearing
  da_energy_offer  — DA energy-only offer clearing
  hsl              — High Sustained Limit per HE

Hits GET /ptp/{root}/{endpoint} for each candidate and prints its datapoint keys.
Run from BESS_Biz/ root:  python shared/scripts/probe_tenaska_endpoints.py
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
from _env_loader import load_env_sections, first  # noqa
from fetch_pnl_data import tenaska_token, PTP_BASE  # reuse cached token

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
ROOT = "ERCOTNodal"

# (index, name) tuples we want to probe
CANDIDATES = [
    (65, "Battery-Settlement-Details"),
    (72, "Generator-Performance"),
    (8,  "Submissions-DA-Energy-Bid"),
    (10, "Submissions-DA-Energy-Only-Offer"),
]

INTERESTING = ("HSL", "BasePoint", "Energy", "RegUp", "RegDown", "RRS",
               "NonSpin", "ECRS", "Award", "Revenue", "Charge", "Discharge",
               "MW", "Price", "Cleared", "Offer", "Bid", "DA", "RT")


def main() -> None:
    sections = load_env_sections(ENV_PATH)
    tk_section = sections.get("tenaska", {})
    token = tenaska_token(tk_section)
    hdrs = {"Authorization": f"Bearer {token}"}

    for idx, name in CANDIDATES:
        print(f"\n{'='*70}\n[{idx}] {name}\n{'='*70}")
        url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(name)}"
        try:
            r = requests.get(url, headers=hdrs, timeout=30)
            r.raise_for_status()
            j = r.json()
        except Exception as e:
            print(f"   ❌ {type(e).__name__}: {e}")
            continue

        data = j.get("data", j)
        if isinstance(data, dict):
            # Try to find datapoint definitions
            dps = (data.get("dataPoints")
                   or data.get("datapoints")
                   or data.get("DataPoints")
                   or [])
            elems = (data.get("elementDefinitions")
                     or data.get("elements")
                     or [])
            keys = list(data.keys())
            print(f"   top-level keys: {keys}")

            # Datapoints
            if dps:
                print(f"   dataPoints ({len(dps)}):")
                for dp in dps:
                    if isinstance(dp, dict):
                        kn = dp.get("keyName") or dp.get("name") or dp.get("key")
                        unit = dp.get("unit") or dp.get("units") or ""
                        marker = "  ⭐" if any(s.lower() in str(kn).lower()
                                              for s in INTERESTING) else ""
                        print(f"     - {kn} ({unit}){marker}")
                    else:
                        print(f"     - {dp}")
            # Element definitions (also try kebab-case key actually returned)
            ed = data.get("element-definitions") or elems
            if ed:
                print(f"   element-definitions ({len(ed)}):")
                for el in ed[:10]:
                    if isinstance(el, dict):
                        print(f"     - name={el.get('name')!r}  identifier={str(el.get('identifier',''))[:36]}")
                    else:
                        print(f"     - {el!r}")
        else:
            print(f"   data is not a dict: {type(data).__name__}")
            print(f"   sample: {str(data)[:300]}")


if __name__ == "__main__":
    main()
