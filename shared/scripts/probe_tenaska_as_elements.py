"""
For each AS-candidate viewport, hit /elements with a date range to enumerate
which actual elements (resources, awards, etc.) exist for our resource.
"""
from __future__ import annotations
import json, sys, urllib.parse, time
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_pnl_data import (  # noqa: E402
    PROJECT_ROOT, ENV_PATH, PTP_BASE,
    tenaska_token, discover_tenaska_endpoints,
)
from _env_loader import load_env_sections  # noqa: E402
import requests

OUT = Path(__file__).resolve().parent / ".cache" / "tenaska_as_elements.json"

DAY = date(2026, 1, 27)

CANDIDATES = [
    "ERCOT_DA_Awards_Prices",
    "DA_Awards_Prices_All",
    "Configuration-Awards",
    "Submissions-AS-Offers-DA-RTC",
    "Generator-Performance",
    "BPDAMT-Summary",
]


def main():
    sections = load_env_sections(ENV_PATH)
    tk = sections.get("tenaska", {})
    eps = discover_tenaska_endpoints(tk)
    token = tenaska_token(tk)
    hdrs = {"Authorization": f"Bearer {token}"}
    root = eps["root"]

    results = {}
    for ep in CANDIDATES:
        url = f"{PTP_BASE}/ptp/{urllib.parse.quote(root)}/{urllib.parse.quote(ep)}/elements"
        params = {
            "begin": DAY.isoformat(),
            "end":   DAY.isoformat(),
        }
        print(f"\n📍 {ep}")
        try:
            r = requests.get(url, headers=hdrs, params=params, timeout=60)
            r.raise_for_status()
            j = r.json()
            data = j.get("data", j)
            # collect element name + def
            els = []
            if isinstance(data, list):
                for el in data:
                    if isinstance(el, dict):
                        els.append({
                            "name": el.get("element") or el.get("name") or el.get("ElementName"),
                            "def":  el.get("definition") or el.get("Definition") or el.get("elementDefinition"),
                            "id":   str(el.get("identifier", ""))[:36],
                        })
            print(f"   total elements: {len(els)}")
            # filter to ours
            ours = [e for e in els if e["name"] and ("Kiskadee" in e["name"] or "GKS" in e["name"])]
            print(f"   our resource: {len(ours)}")
            for e in ours[:8]:
                print(f"     {e['def']:<30} {e['name']:<55} {e['id']}")
            # sample of others to see definitions
            other_defs = sorted({e["def"] for e in els if e["def"]})
            print(f"   distinct definitions in viewport: {other_defs}")
            results[ep] = {
                "total_elements": len(els),
                "our_resource_elements": ours,
                "definitions": other_defs,
            }
        except requests.HTTPError as e:
            print(f"   ❌ HTTP {e.response.status_code}: {e.response.text[:200]}")
            results[ep] = {"error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            print(f"   ❌ {type(e).__name__}: {e}")
            results[ep] = {"error": str(e)}
        time.sleep(1.2)

    OUT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n📄 saved → {OUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
