"""
Probe #76 — locate data for RT_NS_Amt / RT_RRS_Amt / RT_ECRS_Amt (+ CLR_*_Qty)
on Battery-Settlement-Details. They exist in the schema but the standard
ByIdentifier(ESR)/query returned nothing. Try: multiple flowdays, fillNulls,
both element definitions, ByParentAndFilter, query vs query-columnar.
"""
from __future__ import annotations
import base64, json, sys, time, urllib.parse
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
DPS = ["RT_NS_Amt", "RT_RRS_Amt", "RT_ECRS_Amt", "RT_Reg_Up_Amt", "RT_Reg_Down_Amt",
       "CLR_NS_Qty", "CLR_RRS_Qty", "CLR_ECRS_Qty", "CLR_Reg_Up_Qty", "CLR_Reg_Down_Qty",
       "BP_Dev_Amt"]
OUT = Path(__file__).resolve().parents[1] / "raw" / "rt_as_amt_probe.json"


def tok(tk):
    u, p = first(tk, "TENASKA_USERNAME", "USERNAME"), first(tk, "TENASKA_PASSWORD", "PASSWORD")
    b = base64.b64encode(f"{u}:{p}".encode()).decode()
    r = requests.get(f"{BASE}/authentication/token",
                     headers={"Authorization": f"Basic {b}"}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def summarize(j):
    seen = {}
    data = j.get("data", [])
    if isinstance(data, list):
        for el in data:
            elname = el.get("element") or el.get("ElementName")
            for dp in el.get("dataPoints", []) or []:
                vals = [d.get("value") for v in dp.get("values", []) for d in v.get("data", [])]
                nz = [x for x in vals if isinstance(x, (int, float)) and x != 0]
                seen[f"{elname}::{dp.get('keyName')}"] = {"n": len(vals), "nz": len(nz),
                                                          "sample": (nz[:3] or vals[:3])}
    return seen, j.get("validations", [])


def main():
    tk = load_env_sections(PROJECT_ROOT / ".env").get("tenaska", {})
    H = {"Authorization": f"Bearer {tok(tk)}", "Content-Type": "application/json"}
    results = {}

    trials = [
        ("ESR_uuid_query_fillNulls", "query", {
            "elementQueryMode": "ByIdentifier", "elementIdentifiers": [GKS_ESR_UUID],
            "fillNulls": True}),
        ("Kiskadee_Entity_filter", "query", {
            "elementQueryMode": "ByParentAndFilter",
            "elementFilter": [{"elementProperty": "Name", "expression": "contains 'Kiskadee'",
                               "elementDefinition": "Entity"}]}),
        ("Kiskadee_Generator_filter", "query", {
            "elementQueryMode": "ByParentAndFilter",
            "elementFilter": [{"elementProperty": "Name", "expression": "contains 'Kiskadee'",
                               "elementDefinition": "Generator"}]}),
        ("ESR_uuid_columnar", "query-columnar", {
            "elementQueryMode": "ByIdentifier", "elementIdentifiers": [GKS_ESR_UUID]}),
        ("ALL_static_no_filter", "query", {
            "elementQueryMode": "ByParentAndFilter",
            "elementFilter": [{"elementProperty": "Name", "expression": "not null",
                               "elementDefinition": "Entity"}]}),
    ]
    for flowday in ["2026-05-09", "2026-04-15", "2026-02-15", "2026-01-10"]:
        for label, path, extra in trials:
            payload = {"begin": flowday, "end": flowday,
                       "sequenceOptions": "GreatestEnabled", "dataPoints": DPS, **extra}
            key = f"{flowday}|{label}"
            try:
                r = requests.post(f"{BASE}/ptp/{ROOT}/{urllib.parse.quote(EP)}/{path}",
                                  json=payload, headers=H, timeout=120)
                if r.status_code != 200:
                    results[key] = f"HTTP {r.status_code}: {r.text[:160]}"
                else:
                    seen, val = summarize(r.json())
                    results[key] = {"datapoints": seen,
                                    "validations": [f"{v.get('severity')} {v.get('code')} {v.get('message')}"
                                                    for v in val]}
            except Exception as e:
                results[key] = f"{type(e).__name__}: {e}"
            hit = isinstance(results[key], dict) and results[key].get("datapoints")
            print(f"{key:48s} -> {'DATA: '+str(list(results[key]['datapoints'].keys())) if hit else results[key] if isinstance(results[key],str) else 'empty'}"[:200])
            time.sleep(1.2)
        # if any trial for this flowday returned data, stop scanning more dates
        if any(isinstance(v, dict) and v.get("datapoints") for k, v in results.items() if k.startswith(flowday)):
            print(f"  (got data on {flowday} — stopping date scan)")
            break

    OUT.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    print(f"\nsaved -> {OUT}")


if __name__ == "__main__":
    main()
