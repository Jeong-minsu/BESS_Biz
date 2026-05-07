"""
Probe Tenaska PTP viewports for one that exposes DA AS Award MW (and ideally
RT-recleared AS MW under RTC+B) for GKS.

Strategy:
1. List all viewports under root.
2. For viewports whose name mentions AS/Ancillary/Award/AS Capacity/RTAS/etc.,
   hit /elements (cheap — schema only) to inspect available datapoints.
3. Save full mapping for review.
"""
from __future__ import annotations
import json, sys, urllib.parse, time
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

OUT_DIR = Path(__file__).resolve().parent / ".cache"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "tenaska_viewport_inventory.json"


def main():
    sections = load_env_sections(ENV_PATH)
    tk = sections.get("tenaska", {})
    eps = discover_tenaska_endpoints(tk)
    token = tenaska_token(tk)
    hdrs = {"Authorization": f"Bearer {token}"}
    root = eps["root"]

    print(f"📥 Listing all viewports under /ptp/{root}")
    r = requests.get(f"{PTP_BASE}/ptp/{urllib.parse.quote(root)}",
                     headers=hdrs, timeout=30)
    r.raise_for_status()
    raw = r.json().get("data", [])
    if isinstance(raw, dict):
        raw = raw.get("endpoints", [])
    names = [e["name"] if isinstance(e, dict) else str(e) for e in raw]
    print(f"   {len(names)} viewports total")
    for i, n in enumerate(names):
        print(f"     [{i:>2}] {n}")

    # heuristics for AS-related viewports
    keywords = ["AS", "Ancillary", "Award", "RRS", "ECRS", "NonSpin", "NS", "Reg",
                "Service", "RTAS", "DAM", "MCPC", "Capacity"]
    candidates = [n for n in names
                  if any(k.lower() in n.lower() for k in keywords)]
    # de-dup, keep order
    seen = set(); cands = []
    for c in candidates:
        if c not in seen:
            seen.add(c); cands.append(c)

    print(f"\n🔎 AS-related candidates ({len(cands)}):")
    for c in cands:
        print(f"     • {c}")

    inventory: dict[str, dict] = {}
    for ep in cands:
        url = f"{PTP_BASE}/ptp/{urllib.parse.quote(root)}/{urllib.parse.quote(ep)}"
        try:
            r = requests.get(url, headers=hdrs, timeout=30)
            r.raise_for_status()
            schema = r.json()
            data = schema.get("data", schema)
            # try to extract: elementDefinitions, dataPoints
            datapoints = []
            elementdefs = []
            if isinstance(data, dict):
                # different shapes possible
                eds = data.get("ElementDefinitions") or data.get("elementDefinitions") or []
                for ed in eds:
                    if isinstance(ed, dict):
                        elementdefs.append(ed.get("Name") or ed.get("name"))
                        for dp in ed.get("DataPoints", []) or ed.get("dataPoints", []) or []:
                            if isinstance(dp, dict):
                                kn = dp.get("KeyName") or dp.get("keyName") or dp.get("Name")
                                if kn:
                                    datapoints.append(kn)
                # sometimes top-level
                tp = data.get("DataPoints") or data.get("dataPoints") or []
                for dp in tp:
                    if isinstance(dp, dict):
                        kn = dp.get("KeyName") or dp.get("keyName") or dp.get("Name")
                        if kn:
                            datapoints.append(kn)
            datapoints = sorted(set(datapoints))
            elementdefs = sorted(set(filter(None, elementdefs)))
            inventory[ep] = {
                "elementDefinitions": elementdefs,
                "dataPoints": datapoints,
            }
            print(f"\n   📍 {ep}")
            print(f"      defs: {elementdefs}")
            print(f"      datapoints ({len(datapoints)}): {datapoints[:25]}"
                  + (f" ... +{len(datapoints)-25} more" if len(datapoints) > 25 else ""))
        except requests.HTTPError as e:
            print(f"   ❌ {ep}: HTTP {e.response.status_code}")
            inventory[ep] = {"error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            print(f"   ❌ {ep}: {type(e).__name__}: {e}")
            inventory[ep] = {"error": str(e)}
        time.sleep(1.1)

    OUT.write_text(json.dumps({
        "root": root,
        "all_viewports": names,
        "as_candidates_inventory": inventory,
    }, indent=2), encoding="utf-8")
    print(f"\n📄 saved → {OUT.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
