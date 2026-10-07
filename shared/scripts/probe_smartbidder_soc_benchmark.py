"""Probe /soc-detailed for the benchmark strategy across the YTD window."""
from __future__ import annotations
import json, sys
from datetime import date
from pathlib import Path
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _env_loader import load_env_sections, first
from fetch_pnl_data import smartbidder_token, SMARTBIDDER_BASE, BENCHMARK_NAME

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def main():
    sb = load_env_sections(ENV_PATH).get("smartbidder", {})
    token = smartbidder_token(sb)
    client   = first(sb, "SMARTBIDDER_CLIENT", default="apex")
    resource = first(sb, "Resource", "SMARTBIDDER_RESOURCE", default="Kiskadee Storage")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # 3-day slice first, to verify schema and benchmark strategy availability
    params = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": "2026-04-01T00:00:00-05:00",
        "end_date":   "2026-04-04T00:00:00-05:00",
        "return_format": "json",
        "strategy":   BENCHMARK_NAME,
    }
    print(f"GET /soc-detailed  3-day probe  strategy={BENCHMARK_NAME!r}")
    r = requests.get(f"{SMARTBIDDER_BASE}/soc-detailed", params=params, headers=headers, timeout=120)
    print(f"  status={r.status_code}  len={len(r.text)}")
    if r.status_code == 204:
        print("  204 No Content — benchmark SoC not available; will retry without strategy")
    elif r.status_code < 400:
        j = r.json()
        if isinstance(j, dict) and "columns" in j:
            print(f"  columns: {j['columns']}")
            print(f"  rows:    {len(j['data'])}")
            for row in j["data"][:3]:
                print(f"    {row}")
        else:
            print(f"  shape: {type(j).__name__}")
            print(f"  body[:600]: {json.dumps(j)[:600]}")
    else:
        print(f"  body: {r.text[:500]}")

    # Also probe without strategy (realized SoC) for comparison
    p2 = dict(params); p2.pop("strategy", None)
    print(f"\nGET /soc-detailed  3-day probe  (no strategy → realized)")
    r = requests.get(f"{SMARTBIDDER_BASE}/soc-detailed", params=p2, headers=headers, timeout=120)
    print(f"  status={r.status_code}  len={len(r.text)}")
    if r.status_code < 400 and r.text:
        j = r.json()
        if isinstance(j, dict) and "columns" in j:
            print(f"  columns: {j['columns']}")
            print(f"  rows:    {len(j['data'])}")
            for row in j["data"][:3]:
                print(f"    {row}")


if __name__ == "__main__":
    main()
