"""Test BSD via /query (row-shape) and various filter modes to isolate the 500."""
from __future__ import annotations
import json, sys, urllib.parse
from pathlib import Path
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections
from fetch_pnl_data import tenaska_token, PTP_BASE

ROOT = "ERCOTNodal"
ENDPOINT = "Battery-Settlement-Details"
FLOWDAY = "2026-05-03"

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

def main():
    sections = load_env_sections(ENV_PATH)
    tk = tenaska_token(sections.get("tenaska", {}))
    H = {"Authorization": f"Bearer {tk}", "Content-Type": "application/json"}

    # First, get the actual identifier for "Great Kiskadee Storage - ESR"
    el_url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(ENDPOINT)}/elements"
    r = requests.get(el_url, params={"begin": FLOWDAY, "end": FLOWDAY}, headers=H, timeout=30)
    elements = r.json().get("data", [])
    print("Available elements:")
    for e in elements:
        if isinstance(e, dict):
            print(f"  • {e!r}")
        else:
            print(f"  • {e!r}")

    # find ESR identifier
    esr_id = None
    for e in elements:
        if isinstance(e, dict):
            n = e.get("name") or e.get("ElementName") or ""
            if "ESR" in str(n):
                esr_id = e.get("identifier") or e.get("Identifier")
                print(f"\n  → ESR identifier: {esr_id}")

    tests = [
        ("query-columnar | filter Kiskadee | def Entity",
         "query-columnar",
         {"begin": FLOWDAY, "end": FLOWDAY, "elementQueryMode": "ByParentAndFilter",
          "elementFilter": [{"elementProperty": "Name", "expression": "contains 'Kiskadee'",
                             "elementDefinition": "Entity"}]}),
        ("query-columnar | NO filter (mode=All)",
         "query-columnar",
         {"begin": FLOWDAY, "end": FLOWDAY, "elementQueryMode": "All"}),
        ("query-columnar | by identifier (UUID)",
         "query-columnar",
         {"begin": FLOWDAY, "end": FLOWDAY, "elementQueryMode": "ByIdentifier",
          "elementIdentifiers": [esr_id] if esr_id else []}),
        ("query (row) | filter Kiskadee | def Entity",
         "query",
         {"begin": FLOWDAY, "end": FLOWDAY, "elementQueryMode": "ByParentAndFilter",
          "elementFilter": [{"elementProperty": "Name", "expression": "contains 'Kiskadee'",
                             "elementDefinition": "Entity"}]}),
        ("query (row) | by identifier (UUID)",
         "query",
         {"begin": FLOWDAY, "end": FLOWDAY, "elementQueryMode": "ByIdentifier",
          "elementIdentifiers": [esr_id] if esr_id else []}),
    ]

    for label, path, payload in tests:
        print(f"\n--- {label} ---")
        url = f"{PTP_BASE}/ptp/{ROOT}/{urllib.parse.quote(ENDPOINT)}/{path}"
        try:
            r = requests.post(url, json=payload, headers=H, timeout=60)
            print(f"  status={r.status_code}")
            if r.status_code == 200:
                j = r.json()
                d = j.get("data", {})
                if isinstance(d, dict):
                    print(f"  Elements: {len(d.get('Elements', []))}")
                    print(f"  IntervalStartUtc count: {len(d.get('IntervalStartUtc', []))}")
                else:
                    print(f"  data type: {type(d).__name__} len: {len(d) if hasattr(d, '__len__') else '?'}")
                vals = j.get("validations", [])
                if vals:
                    print(f"  validations: {vals}")
            else:
                print(f"  body: {r.text[:300]}")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
