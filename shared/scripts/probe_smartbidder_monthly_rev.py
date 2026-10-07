"""One-off probe: pull benchmark /revenue for 2026-01-01..today at monthly resolution
and dump shape + a sample. Strategy = AA - Mount Blue Sky with Virtuals (RTC version).
"""
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
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()
    params = {
        "client": client, "iso": "ERCOT", "resource": resource,
        "start_date": "2026-01-01T00:00:00-06:00",
        "end_date":   f"{today.isoformat()}T00:00:00-05:00",
        "return_format": "json",
        "strategy":   BENCHMARK_NAME,
        "resolution": "monthly",
    }
    for resolution in ("monthly", "daily", "hourly"):
        p = dict(params, resolution=resolution)
        print(f"\nGET /revenue  resolution={resolution}  range=2026-01-01..{today}  strategy={BENCHMARK_NAME!r}")
        r = requests.get(f"{SMARTBIDDER_BASE}/revenue", params=p, headers=headers, timeout=180)
        print(f"  status={r.status_code}  body_len={len(r.text)}")
        if r.status_code == 204:
            print("  204 No Content"); continue
        if r.status_code >= 400:
            print(f"  body: {r.text[:1000]}"); continue
        j = r.json()
        if isinstance(j, dict) and "columns" in j:
            cols = j["columns"]; data = j["data"]
            print(f"  columns: {cols}")
            print(f"  rows:    {len(data)}")
            for row in data[:5]:
                print(f"    {row}")
            if data:
                print(f"    ... (last)")
                print(f"    {data[-1]}")
        else:
            print(f"  json shape: {type(j).__name__} keys: {list(j)[:10] if hasattr(j,'keys') else 'n/a'}")
            print(f"  body[:800]: {json.dumps(j)[:800]}")
        if resolution != "hourly" and isinstance(j, dict) and j.get("data"):
            break  # found data — stop early


if __name__ == "__main__":
    main()
