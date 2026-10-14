"""
P&L Manager — yesterday's GKS actuals fetch (production)

Run from BESS_Biz/ root:
    python shared/scripts/fetch_pnl_data.py
    python shared/scripts/fetch_pnl_data.py --flowday 2026-04-29

Pulls (per agents/pnl-manager.md):
- Tenaska PTP   — Energy & AS Details, HSL, DA Energy Bid, DA Energy-only Offer

The Smartbidder benchmark (Mount Blue Sky) was dropped when the subscription
ended (2026-10). Tyba has no benchmark/shadow-asset API yet — no replacement.

First run automatically discovers Tenaska PTP {ROOT} and {ENDPOINT} slugs and
caches them to shared/scripts/.tenaska_endpoints.json so subsequent runs go
straight to /query-columnar.

Required .env keys:
    TENASKA_USERNAME, TENASKA_PASSWORD   (or USERNAME/PASSWORD under the Tenaska header)
    TENASKA_RESOURCE_FILTER              (optional, default: Kiskadee)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from _env_loader import load_env_sections, first  # local helper

# ---------- Paths ----------
PROJECT_ROOT = Path(__file__).resolve().parents[2]   # BESS_Biz/
ENV_PATH     = PROJECT_ROOT / ".env"
RAW_DIR      = PROJECT_ROOT / "shared" / "data"
PNL_DIR      = RAW_DIR / "pnl" / "gks" / "hourly"
CACHE_DIR    = Path(__file__).resolve().parent / ".cache"
ENDPOINT_CACHE = CACHE_DIR / "tenaska_endpoints.json"
TOKEN_CACHE    = CACHE_DIR / "tenaska_token.json"

PTP_BASE         = "https://api.ptp.energy"


# ---------- Tenaska auth (Basic → Bearer, 24h cache) ----------
def tenaska_token(tk_section: dict[str, str]) -> str:
    """tk_section: 'tenaska' section dict from load_env_sections().
    Accepts generic USERNAME/PASSWORD (current .env) or TENASKA_USERNAME/TENASKA_PASSWORD."""
    user = first(tk_section, "TENASKA_USERNAME", "USERNAME")
    pwd  = first(tk_section, "TENASKA_PASSWORD", "PASSWORD")
    if not user or not pwd:
        sys.exit("❌ Tenaska USERNAME / PASSWORD missing in [tenaska] section of .env")

    # cache check
    if TOKEN_CACHE.exists():
        cached = json.loads(TOKEN_CACHE.read_text())
        age = time.time() - cached.get("ts", 0)
        if age < 23 * 3600 and cached.get("token"):
            return cached["token"]

    basic = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    r = requests.get(f"{PTP_BASE}/authentication/token",
                     headers={"Authorization": f"Basic {basic}"}, timeout=30)
    if r.status_code == 401:
        sys.exit("❌ Tenaska 401 — credentials rejected")
    r.raise_for_status()
    token = r.json()["data"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps({"token": token, "ts": time.time()}))
    return token


# ---------- Tenaska endpoint discovery (1-time, cached) ----------
def discover_tenaska_endpoints(tk_section: dict[str, str]) -> dict[str, str]:
    """
    First run: hits /ptp and /ptp/{root} to enumerate Viewports, prints them,
    asks user to map by slug, saves cache. Subsequent runs read cache.
    """
    if ENDPOINT_CACHE.exists():
        cached = json.loads(ENDPOINT_CACHE.read_text())
        if all(k in cached for k in ("root", "energy_as_detail", "da_energy_bid",
                                     "da_energy_offer", "hsl")):
            print(f"📂 Using cached Tenaska endpoint mapping from {ENDPOINT_CACHE}")
            return cached

    token = tenaska_token(tk_section)
    hdrs = {"Authorization": f"Bearer {token}"}

    print("🔎 Tenaska endpoint discovery (1-time setup)")
    print("   Listing accessible markets ...")
    r = requests.get(f"{PTP_BASE}/ptp", headers=hdrs, timeout=30)
    r.raise_for_status()
    markets = r.json().get("data", [])
    print(f"\n   Markets ({len(markets)}):")
    for i, m in enumerate(markets):
        print(f"     [{i}] name={m.get('name')!r}  id={str(m.get('identifier',''))[:36]}")

    # non-interactive mode: TENASKA_MARKET_INDEX env var or single-market auto-pick
    env_pick = os.environ.get("TENASKA_MARKET_INDEX")
    if env_pick is not None:
        pick = env_pick.strip()
        print(f"   (TENASKA_MARKET_INDEX={pick!r} from env)")
    elif len(markets) == 1:
        pick = "0"
        print("   (single market — auto-picking [0])")
    else:
        try:
            pick = input("\n   Pick market index (default 0): ").strip() or "0"
        except EOFError:
            sys.exit("❌ Multiple markets and no interactive stdin. "
                     "Set TENASKA_MARKET_INDEX=<idx> in env "
                     "(0=ERCOTNodal, 1=Operations) and re-run.")
    root = markets[int(pick)]["name"]
    print(f"   → root = {root!r}")

    print(f"\n   Listing endpoints under /ptp/{root} ...")
    r = requests.get(f"{PTP_BASE}/ptp/{urllib.parse.quote(root)}",
                     headers=hdrs, timeout=30)
    r.raise_for_status()
    raw = r.json().get("data", [])
    # /ptp/{root} returns either a list directly, or a dict with an "endpoints" sub-key
    if isinstance(raw, dict):
        endpoints = raw.get("endpoints", [])
    else:
        endpoints = raw
    # /ptp/{root} may return either list[dict] (with name/identifier)
    # or list[str] (just slug names) — normalize.
    def _ep_name(e: Any) -> str:
        return e["name"] if isinstance(e, dict) else str(e)

    def _ep_id(e: Any) -> str:
        return str(e.get("identifier", "")) if isinstance(e, dict) else ""

    print(f"\n   Endpoints ({len(endpoints)}):")
    for i, e in enumerate(endpoints):
        print(f"     [{i}] name={_ep_name(e)!r}  id={_ep_id(e)[:36]}")

    def pick_endpoint(label: str, hint: str, env_key: str) -> str:
        env_idx = os.environ.get(env_key)
        if env_idx is not None:
            idx = env_idx.strip()
            print(f"   ({env_key}={idx!r} from env for '{label}')")
        else:
            try:
                idx = input(f"\n   Pick index for '{label}' ({hint}): ").strip()
            except EOFError:
                sys.exit(f"❌ No interactive stdin for '{label}'. "
                         f"Set {env_key}=<idx> in env and re-run.")
        return _ep_name(endpoints[int(idx)])

    mapping = {
        "root": root,
        "energy_as_detail": pick_endpoint("Energy & AS Details",
                                          "yesterday's actuals: energy + AS",
                                          "TENASKA_EP_ENERGY_AS"),
        "da_energy_bid":    pick_endpoint("DA Energy Bid Market Result",
                                          "DA energy bid clearing",
                                          "TENASKA_EP_DA_BID"),
        "da_energy_offer":  pick_endpoint("DA Energy Only Offer Market Result",
                                          "DA energy-only offer clearing",
                                          "TENASKA_EP_DA_OFFER"),
        "hsl":              pick_endpoint("HSL",
                                          "may be same as Energy & AS Details",
                                          "TENASKA_EP_HSL"),
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ENDPOINT_CACHE.write_text(json.dumps(mapping, indent=2))
    print(f"\n✅ Saved mapping → {ENDPOINT_CACHE}")
    return mapping


# ---------- Tenaska query ----------
def tenaska_query(token: str, root: str, endpoint: str,
                  flowday: date, resource_filter: str,
                  datapoints: list[str] | None = None,
                  extra_filters: list[dict] | None = None,
                  element_definition: str = "Generator",
                  path: str = "query-columnar",
                  element_identifiers: list[str] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "begin": flowday.isoformat(),
        "end":   flowday.isoformat(),
        "sequenceOptions":  "GreatestEnabled",
    }
    if element_identifiers:
        payload["elementQueryMode"] = "ByIdentifier"
        payload["elementIdentifiers"] = element_identifiers
    else:
        payload["elementQueryMode"] = "ByParentAndFilter"
        payload["elementFilter"] = [
            {"elementProperty": "Name",
             "expression": f"contains '{resource_filter}'",
             "elementDefinition": element_definition},
        ] + (extra_filters or [])
    if datapoints:
        payload["dataPoints"] = datapoints

    url = f"{PTP_BASE}/ptp/{urllib.parse.quote(root)}/{urllib.parse.quote(endpoint)}/{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=120)
    if r.status_code >= 400:
        print(f"     ❌ {r.status_code} body: {r.text[:500]}")
    r.raise_for_status()
    j = r.json()

    # surface validation warnings/errors
    for v in j.get("validations", []):
        sev = v.get("severity", "?")
        code = v.get("code", "?")
        msg = v.get("message", "?")
        prefix = "  ⚠️" if sev == "Warning" else "  ❌"
        print(f"{prefix} Tenaska validation [{sev} {code}]: {msg}")

    return j


def flatten_query(j: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten Tenaska PTP response — handles both shapes:

    /query-columnar (verified 2026-05-04):
      data = {IntervalStartUtc:[ts...], IntervalEndUtc:[ts...],
              Elements:[{ElementName, Definition, DataPoints:{key:[vals...]}}]}

    /query (row shape):
      data = [{element, definition, dataPoints:[
                  {keyName, values:[{intervalStartUtc, intervalEndUtc,
                                     data:[{value, sequence}]}]}]}]
    """
    rows: list[dict[str, Any]] = []
    data = j.get("data", j)

    # row-shape (/query)
    if isinstance(data, list):
        for el in data:
            if not isinstance(el, dict):
                continue
            elname = el.get("element") or el.get("ElementName") or el.get("name")
            eldef  = el.get("definition") or el.get("Definition")
            for dp in el.get("dataPoints", []) or []:
                kn = dp.get("keyName") or dp.get("name")
                for v in dp.get("values", []) or []:
                    for d in v.get("data", []) or []:
                        rows.append({
                            "element": elname,
                            "definition": eldef,
                            "datapoint": kn,
                            "interval_start_utc": v.get("intervalStartUtc"),
                            "interval_end_utc":   v.get("intervalEndUtc"),
                            "value": d.get("value"),
                            "sequence": d.get("sequence"),
                        })
        return rows

    # columnar shape (/query-columnar)
    if isinstance(data, dict):
        starts = data.get("IntervalStartUtc") or data.get("intervalStartUtc") or []
        ends   = data.get("IntervalEndUtc")   or data.get("intervalEndUtc")   or []
        elements = data.get("Elements") or data.get("elements") or []
        for el in elements:
            if not isinstance(el, dict):
                continue
            elname = el.get("ElementName") or el.get("name") or el.get("element")
            eldef  = el.get("Definition")  or el.get("elementDefinition")
            dps = el.get("DataPoints") or el.get("dataPoints") or {}
            if not isinstance(dps, dict):
                continue
            for kn, series in dps.items():
                if not isinstance(series, list):
                    continue
                for i, val in enumerate(series):
                    rows.append({
                        "element": elname,
                        "definition": eldef,
                        "datapoint": kn,
                        "interval_start_utc": starts[i] if i < len(starts) else None,
                        "interval_end_utc":   ends[i]   if i < len(ends)   else None,
                        "value": val,
                    })
    return rows


# ---------- main ----------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--flowday", default=None,
                    help="Flowday to fetch (YYYY-MM-DD). Default = yesterday.")
    ap.add_argument("--rediscover", action="store_true",
                    help="Force rediscovery of Tenaska endpoints")
    args = ap.parse_args()

    flowday = (date.fromisoformat(args.flowday)
               if args.flowday else date.today() - timedelta(days=1))
    print(f"🎯 Flowday (D-1): {flowday.isoformat()}")

    sections = load_env_sections(ENV_PATH)
    tk_section = sections.get("tenaska", {})
    PNL_DIR.mkdir(parents=True, exist_ok=True)

    # Tenaska resource filter: friendly name (Tenaska Entity/Generator namespace),
    # NOT the ERCOT settlement point ('GKS_BESS_RN' is the settlement node, separate ns).
    # For GKS BESS this is 'Kiskadee' (matches: 'Great Kiskadee Storage, LLC',
    #   'Great Kiskadee Storage, LLC Gen', 'Great Kiskadee Storage - ESR').
    resource_filter = first(tk_section, "TENASKA_RESOURCE_FILTER", default="Kiskadee")
    print(f"   Tenaska resource filter: contains {resource_filter!r}")

    # --- Tenaska ---
    if args.rediscover and ENDPOINT_CACHE.exists():
        ENDPOINT_CACHE.unlink()

    print("\n📥 Tenaska PTP fetch ...")
    endpoints = discover_tenaska_endpoints(tk_section)
    token = tenaska_token(tk_section)

    # Per-endpoint slot config (verified 2026-05-04 via /elements + /query probes):
    # NOTE: Battery-Settlement-Details server returns 500 on /query-columnar — must
    # use /query (row shape) with ByIdentifier (UUID) for the ESR.
    GKS_ESR_UUID = "ef8d8d31-47c4-4212-b893-a2dbb2070a2f"  # 'Great Kiskadee Storage - ESR'
    SLOT_CONFIG = {
        "energy_as_detail": {"def": "Entity",    "filter": None,
                             "path": "query",
                             "ids":  [GKS_ESR_UUID]},
        "hsl":              {"def": "Generator", "filter": "Kiskadee",
                             "path": "query-columnar"},
        # Submissions-* are populated only if WE submit bids via PTP (bids are not
        # submitted through PTP) — expected to be empty.
        "da_energy_bid":    {"def": "Generator", "filter": "154b78dbd0de",
                             "path": "query-columnar"},
        "da_energy_offer":  {"def": "Generator", "filter": "154b78dbd0de",
                             "path": "query-columnar"},
    }

    raw_outputs: dict[str, list[dict[str, Any]]] = {}
    for label, dp_list in [
        ("energy_as_detail", None),
        ("hsl",              None),
        ("da_energy_bid",    None),
        ("da_energy_offer",  None),
    ]:
        ep = endpoints.get(label)
        if not ep:
            print(f"   ⚠️ skipping {label} — no endpoint mapped")
            continue
        cfg = SLOT_CONFIG.get(label, {"def": "Generator", "filter": resource_filter,
                                       "path": "query-columnar"})
        slot_filter = cfg.get("filter")
        el_def = cfg["def"]
        path = cfg.get("path", "query-columnar")
        ids  = cfg.get("ids")
        print(f"   • querying {label} ({ep!r}, def={el_def!r}, path={path}, "
              f"{'ids='+str(ids) if ids else 'filter='+repr(slot_filter)}) ...")
        try:
            j = tenaska_query(token, endpoints["root"], ep, flowday,
                              slot_filter or "", dp_list,
                              element_definition=el_def,
                              path=path,
                              element_identifiers=ids)
            # always save raw response for debugging columnar shape
            raw_out = PNL_DIR / f"{flowday.isoformat()}_{label}_raw.json"
            raw_out.write_text(json.dumps(j, indent=2, default=str), encoding="utf-8")
            rows = flatten_query(j)
            raw_outputs[label] = rows
            out = PNL_DIR / f"{flowday.isoformat()}_{label}.json"
            out.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
            print(f"     saved → {out.relative_to(PROJECT_ROOT)}  ({len(rows)} rows; raw → {raw_out.name})")
        except requests.HTTPError as e:
            print(f"     ❌ HTTPError: {e}")
        except Exception as e:
            print(f"     ❌ {type(e).__name__}: {e}")

    # quick stats
    print("\n📊 Quick stats:")
    energy_rows = raw_outputs.get("energy_as_detail", [])
    if energy_rows:
        # very rough: sum 'value' grouped by datapoint
        from collections import defaultdict
        agg = defaultdict(float)
        for row in energy_rows:
            v = row.get("value")
            if isinstance(v, (int, float)):
                agg[row["datapoint"]] += v
        for k, v in sorted(agg.items()):
            print(f"   • {k:30s} sum={v:>12,.2f}")

    # --- Summary ---
    summary = {
        "flowday": flowday.isoformat(),
        "fetched_at_utc": datetime.utcnow().isoformat() + "Z",
        "tenaska_endpoints_used": endpoints,
        "row_counts": {k: len(v) for k, v in raw_outputs.items()},
    }
    summary_path = PNL_DIR / f"{flowday.isoformat()}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📋 Summary → {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"\n✅ Done. Next: feed {summary_path.name} to pnl-manager agent for daily P&L doc.")


if __name__ == "__main__":
    main()
