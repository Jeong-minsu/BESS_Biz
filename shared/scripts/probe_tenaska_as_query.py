"""
Probe top AS candidate viewports by issuing actual /query for 2026-01-27 to
discover datapoint names.
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

OUT = Path(__file__).resolve().parent / ".cache" / "tenaska_as_probe.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

GKS_ESR_UUID = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"
DAY = date(2026, 1, 27)

CANDIDATES = [
    "ERCOT_DA_Awards_Prices",
    "DA_Awards_Prices_All",
    "Configuration-Awards",
    "Submissions-AS-Offers-DA-RTC",
    "System_AS_Capacity",
    "Ancillary Service Deployment Factors",
    "Generator-Performance",
    "BPDAMT-Summary",
]


def probe_query(token, root, ep, day, hdrs):
    url = f"{PTP_BASE}/ptp/{urllib.parse.quote(root)}/{urllib.parse.quote(ep)}/query"
    # Try ByIdentifier first (works for Battery-Settlement-Details with ESR UUID)
    payloads = [
        {  # ByIdentifier (ESR)
            "begin": day.isoformat(),
            "end":   day.isoformat(),
            "elementQueryMode": "ByIdentifier",
            "elementIdentifiers": [GKS_ESR_UUID],
            "sequenceOptions": "GreatestEnabled",
        },
        {  # ByParentAndFilter on Generator name 'Kiskadee'
            "begin": day.isoformat(),
            "end":   day.isoformat(),
            "elementQueryMode": "ByParentAndFilter",
            "sequenceOptions": "GreatestEnabled",
            "elementFilter": [{"elementProperty": "Name",
                               "expression": "contains 'Kiskadee'",
                               "elementDefinition": "Generator"}],
        },
        {  # ByParentAndFilter on Entity
            "begin": day.isoformat(),
            "end":   day.isoformat(),
            "elementQueryMode": "ByParentAndFilter",
            "sequenceOptions": "GreatestEnabled",
            "elementFilter": [{"elementProperty": "Name",
                               "expression": "contains 'Kiskadee'",
                               "elementDefinition": "Entity"}],
        },
    ]
    for i, p in enumerate(payloads):
        try:
            r = requests.post(url, json=p, headers=hdrs, timeout=120)
            if r.status_code == 200:
                j = r.json()
                # collect datapoint keynames
                dps = set()
                el_names = set()
                el_defs = set()
                data = j.get("data", j)
                if isinstance(data, list):
                    for el in data:
                        el_names.add(el.get("element"))
                        el_defs.add(el.get("definition"))
                        for dp in el.get("dataPoints", []) or []:
                            kn = dp.get("keyName") or dp.get("name")
                            if kn: dps.add(kn)
                elif isinstance(data, dict):
                    for el in (data.get("Elements") or []):
                        el_names.add(el.get("ElementName"))
                        el_defs.add(el.get("Definition"))
                        for kn in (el.get("DataPoints") or {}).keys():
                            dps.add(kn)
                vals = j.get("validations", [])
                err = [v for v in vals if v.get("severity") == "Error"]
                return {
                    "mode": ["ByIdentifier", "ByParent-Generator", "ByParent-Entity"][i],
                    "status": 200,
                    "elements": sorted(el_names),
                    "definitions": sorted(filter(None, el_defs)),
                    "datapoints": sorted(dps),
                    "validation_errors": err,
                }
            elif r.status_code in (400, 422):
                continue  # try next payload
            else:
                return {"mode": ["ByIdentifier","ByParent-Generator","ByParent-Entity"][i],
                        "status": r.status_code, "body": r.text[:300]}
        except Exception as e:
            return {"mode": ["ByIdentifier","ByParent-Generator","ByParent-Entity"][i],
                    "error": f"{type(e).__name__}: {e}"}
    return {"status": "all_payloads_failed"}


def main():
    sections = load_env_sections(ENV_PATH)
    tk = sections.get("tenaska", {})
    eps = discover_tenaska_endpoints(tk)
    token = tenaska_token(tk)
    hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    root = eps["root"]

    results = {}
    for ep in CANDIDATES:
        print(f"\n📍 {ep}")
        res = probe_query(token, root, ep, DAY, hdrs)
        results[ep] = res
        if res.get("status") == 200:
            print(f"   mode={res['mode']}  elements={res['elements'][:3]}")
            print(f"   defs={res['definitions']}")
            print(f"   datapoints ({len(res['datapoints'])}): {res['datapoints']}")
        else:
            print(f"   {res}")
        time.sleep(1.2)

    OUT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n📄 saved → {OUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
