"""Diagnose Smartbidder /revenue 400."""
from __future__ import annotations
import json, sys
from datetime import date, timedelta
from pathlib import Path
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections, first
from fetch_pnl_data import smartbidder_token, SMARTBIDDER_BASE, BENCHMARK_NAME

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
FLOWDAY = date.fromisoformat("2026-05-03")
NEXT    = FLOWDAY + timedelta(days=1)


def main():
    sections = load_env_sections(ENV_PATH)
    sb = sections.get("smartbidder", {})
    print(f"section keys: {list(sb.keys())}")
    print(f"  CLIENT_ID present: {'CLIENT_ID' in sb}")
    print(f"  Resource value:    {sb.get('Resource', '<unset>')!r}")
    print(f"  Node value:        {sb.get('Node', '<unset>')!r}")
    print(f"  SMARTBIDDER_CLIENT default would be {first(sb,'SMARTBIDDER_CLIENT', default='apex')!r}")
    print()

    token = smartbidder_token(sb)
    print(f"  ✅ token acquired ({len(token)} chars)")

    client   = first(sb, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sb, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")

    headers = {"Authorization": f"Bearer {token}"}

    # 1) try the original call
    print("\n--- 1) original /revenue call ---")
    params = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": f"{FLOWDAY.isoformat()}T00:00:00-05:00",
        "end_date":   f"{NEXT.isoformat()}T00:00:00-05:00",
        "return_format": "json",
        "strategy":   BENCHMARK_NAME,
        "resolution": "daily",
    }
    print(f"  params: {params}")
    r = requests.get(f"{SMARTBIDDER_BASE}/revenue", params=params, headers=headers, timeout=60)
    print(f"  status={r.status_code}")
    print(f"  body: {r.text[:1000]}")

    # 2) try without strategy
    print("\n--- 2) /revenue without 'strategy' ---")
    p2 = dict(params); p2.pop("strategy", None)
    r = requests.get(f"{SMARTBIDDER_BASE}/revenue", params=p2, headers=headers, timeout=60)
    print(f"  status={r.status_code}")
    print(f"  body: {r.text[:600]}")

    # 3) list available resources via /resources or /strategies if such endpoint exists
    print("\n--- 3) probe metadata endpoints ---")
    for ep in ("/resources", "/strategies", "/clients", "/iso"):
        try:
            r = requests.get(f"{SMARTBIDDER_BASE}{ep}",
                             params={"client": client, "iso": "ERCOT"},
                             headers=headers, timeout=30)
            print(f"  GET {ep} → {r.status_code}  body[:300]: {r.text[:300]}")
        except Exception as e:
            print(f"  GET {ep} → ❌ {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
