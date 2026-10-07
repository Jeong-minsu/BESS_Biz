"""
Probe #71 — find Tenaska PTP viewport(s) that expose RT AS (NonSpin/RRS/ECRS) revenue.

Battery-Settlement-Details only has DA_*_Amt + RT_Ancillary_Imbalance_Amt (all zero).
RT AS revenue must live in another viewport. Probe candidates' schema + a sample query
for the GKS ESR on a recent flowday, dump every datapoint name + nonzero sample.
"""
from __future__ import annotations
import base64, json, sys, time, urllib.parse
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
GKS_ESR_UUID = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"
FLOWDAY = date(2026, 5, 9)
OUT = Path(__file__).resolve().parents[1] / "raw" / "tenaska_rt_as_probe.json"

CANDIDATES = [
    "Settlement-Charge-Details",
    "Settlement-Charge-Details-Market-Versioned",
    "Real-Time-Settlement-Amounts",
    "Real_Time_Daily_Settlement",
    "Generator-Settlement-Data",
    "DART-Energy-Details",
    "Real-Time-Unit-Position",
    "Estimated-Settlement-Amounts",
    "Settlement-Summary",
    "ERCOT-Statement-Values",
]


def token(tk):
    u, p = first(tk, "TENASKA_USERNAME", "USERNAME"), first(tk, "TENASKA_PASSWORD", "PASSWORD")
    basic = base64.b64encode(f"{u}:{p}".encode()).decode()
    r = requests.get(f"{BASE}/authentication/token",
                     headers={"Authorization": f"Basic {basic}"}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def main():
    tk = load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {})
    tok = token(tk)
    H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    results = {}

    for vp in CANDIDATES:
        entry = {}
        # 1. schema
        try:
            r = requests.get(f"{BASE}/ptp/{ROOT}/{urllib.parse.quote(vp)}",
                             headers=H, timeout=30)
            entry["schema_status"] = r.status_code
            if r.status_code == 200:
                j = r.json().get("data", r.json())
                # datapoint names can live under several keys depending on shape
                dps = j.get("dataPoints") or j.get("DataPoints") or []
                if isinstance(dps, list):
                    entry["schema_datapoints"] = [
                        (d.get("keyName") or d.get("name") or d) if isinstance(d, dict) else d
                        for d in dps]
                entry["schema_defs"] = j.get("elementDefinitions") or j.get("ElementDefinitions")
        except Exception as e:
            entry["schema_err"] = f"{type(e).__name__}: {e}"

        # 2. sample query for GKS ESR (try ByIdentifier on /query)
        for mode, payload in [
            ("ByIdentifier", {"begin": FLOWDAY.isoformat(), "end": FLOWDAY.isoformat(),
                              "elementQueryMode": "ByIdentifier",
                              "elementIdentifiers": [GKS_ESR_UUID],
                              "sequenceOptions": "GreatestEnabled"}),
            ("ByParentAndFilter", {"begin": FLOWDAY.isoformat(), "end": FLOWDAY.isoformat(),
                                   "elementQueryMode": "ByParentAndFilter",
                                   "elementFilter": [{"elementProperty": "Name",
                                                      "expression": "contains 'Kiskadee'",
                                                      "elementDefinition": "Entity"}],
                                   "sequenceOptions": "GreatestEnabled"}),
        ]:
            try:
                r = requests.post(f"{BASE}/ptp/{ROOT}/{urllib.parse.quote(vp)}/query",
                                  json=payload, headers=H, timeout=90)
                if r.status_code != 200:
                    entry[f"query_{mode}"] = f"HTTP {r.status_code}: {r.text[:160]}"
                    continue
                j = r.json()
                data = j.get("data", [])
                seen = {}
                if isinstance(data, list):
                    for el in data:
                        for dp in el.get("dataPoints", []) or []:
                            kn = dp.get("keyName")
                            vals = [d.get("value") for v in dp.get("values", [])
                                    for d in v.get("data", [])]
                            nz = [x for x in vals if isinstance(x, (int, float)) and x != 0]
                            seen[kn] = {"n": len(vals), "nonzero": len(nz),
                                        "sample": nz[:3] if nz else vals[:3]}
                entry[f"query_{mode}"] = {"n_elements": len(data) if isinstance(data, list) else "?",
                                          "datapoints": seen}
                entry[f"query_{mode}_validations"] = j.get("validations", [])
                if seen:
                    break  # got data, no need for other mode
            except Exception as e:
                entry[f"query_{mode}"] = f"{type(e).__name__}: {e}"
            time.sleep(1.1)
        results[vp] = entry
        print(f"--- {vp} ---")
        print(json.dumps(entry, indent=1, default=str)[:1500])
        print()
        time.sleep(1.1)

    OUT.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
