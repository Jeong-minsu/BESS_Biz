"""
#90 — Direct Tenaska Generator-Performance HSL fetch (corrected param schema).

fetch_pnl_data.py used filter='Kiskadee' which returns 500 for historical dates.
Correct param is elementIdentifiers=<UUID> with query-columnar — verified working
for 2026-01-15.

Fetches Telemetered_HSL_5_Min + Predictive_HSL_15_Min for 2026-01-01 ~ 2026-05-17.
Saves hourly aggregation to derived/tenaska_hsl_hourly.parquet.
"""
from __future__ import annotations
import json, sys, time
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))
from _env_loader import load_env_sections           # noqa
from fetch_pnl_data import tenaska_token, PTP_BASE  # noqa

ADHOC = Path(__file__).resolve().parents[1]
DERIVED = ADHOC / "derived"
RAW = ADHOC / "raw" / "tenaska_hsl_raw"
RAW.mkdir(parents=True, exist_ok=True)

GKS_ESR_UUID = "b94b48e7-51ac-4d6c-abf4-26531ab91384"   # 'Great Kiskadee Storage ESR'
START = date(2026, 1, 1)
END   = date(2026, 5, 17)
DATA_POINTS = "Telemetered_HSL_5_Min;Predictive_HSL_15_Min"


def parse_columnar(j: dict, flowday: date) -> list[dict]:
    """Convert columnar response → row format."""
    data = j.get("data", {}) or {}
    starts = data.get("IntervalStartUtc", []) or []
    ends   = data.get("IntervalEndUtc", []) or []
    if not starts:
        return []
    rows = []
    # Each non-time key is a datapoint name → list of values aligned with starts
    for key, vals in data.items():
        if key in ("IntervalStartUtc", "IntervalEndUtc"):
            continue
        if not isinstance(vals, list):
            continue
        for i, v in enumerate(vals):
            if v is None: continue
            # value might be a dict or scalar; usually scalar in columnar format
            if isinstance(v, dict):
                v = v.get("value") or v.get("Value")
            if v is None: continue
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            rows.append({
                "interval_start_utc": starts[i],
                "interval_end_utc":   ends[i] if i < len(ends) else None,
                "datapoint": key,
                "value": v,
            })
    return rows


def fetch_one(token: str, flowday: date) -> list[dict]:
    hdrs = {"Authorization": f"Bearer {token}"}
    params = {
        "begin": flowday.isoformat(),
        "end":   flowday.isoformat(),
        "elementIdentifiers": GKS_ESR_UUID,
        "elementDefinitions": "Generator",
        "dataPoints": DATA_POINTS,
        "fillNulls": "false",
    }
    url = f"{PTP_BASE}/ptp/ERCOTNodal/Generator-Performance/query-columnar"
    r = requests.get(url, params=params, headers=hdrs, timeout=60)
    if r.status_code != 200:
        return []
    j = r.json()
    # Save raw for reference
    (RAW / f"{flowday.isoformat()}.json").write_text(json.dumps(j), encoding="utf-8")
    return parse_columnar(j, flowday)


def main() -> None:
    token = tenaska_token(load_env_sections(ROOT / ".env").get("tenaska", {}))
    print(f"Fetching Tenaska HSL: {START} → {END} ({(END-START).days + 1} days)")
    print("Rate limit: 1 call per 1.5s")
    print()

    all_rows = []
    ok = fail = empty = 0
    t0 = time.time()
    d = START
    i = 0
    total = (END - START).days + 1
    while d <= END:
        i += 1
        try:
            rows = fetch_one(token, d)
            if rows:
                all_rows.extend(rows)
                ok += 1
                if i % 10 == 0 or i == total:
                    print(f"  [{i}/{total}] {d}: {len(rows)} rows  (cumulative {len(all_rows):,})")
            else:
                empty += 1
                print(f"  [{i}/{total}] {d}: EMPTY")
        except Exception as e:
            fail += 1
            print(f"  [{i}/{total}] {d}: FAIL  {type(e).__name__}: {e}")
        time.sleep(1.5)
        d += timedelta(days=1)

    elapsed = time.time() - t0
    print()
    print(f"Done. ok={ok}, empty={empty}, fail={fail}, elapsed={elapsed/60:.1f} min")
    print(f"Total rows fetched: {len(all_rows):,}")

    # Aggregate to hourly
    if not all_rows:
        print("No data — aborting aggregation.")
        return
    df = pd.DataFrame(all_rows)
    df["datetime_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    df["hour_ct"] = df["datetime_utc"].dt.tz_convert("America/Chicago").dt.floor("h")

    hourly_frames = []
    for dp, short in [("Telemetered_HSL_5_Min",   "tenaska_hsl_telemetered"),
                      ("Predictive_HSL_15_Min",   "tenaska_hsl_predictive")]:
        sub = df[df["datapoint"] == dp]
        if sub.empty:
            continue
        agg = sub.groupby("hour_ct")["value"].mean().reset_index()
        agg = agg.rename(columns={"value": short, "hour_ct": "datetime_ct"})
        hourly_frames.append(agg)

    if not hourly_frames:
        print("Aggregation failed.")
        return
    hourly = hourly_frames[0]
    for fr in hourly_frames[1:]:
        hourly = hourly.merge(fr, on="datetime_ct", how="outer")
    hourly = hourly.sort_values("datetime_ct").reset_index(drop=True)
    out = DERIVED / "tenaska_hsl_hourly.parquet"
    hourly.to_parquet(out, index=False)
    print(f"\nHourly aggregation: {len(hourly)} hours")
    print(f"  range: {hourly['datetime_ct'].min()} ~ {hourly['datetime_ct'].max()}")
    for c in hourly.columns:
        if c == "datetime_ct": continue
        s = hourly[c].dropna()
        if len(s):
            print(f"  {c}: n={len(s)}, mean={s.mean():.2f}, min={s.min():.2f}, max={s.max():.2f}")
    print(f"\nsaved -> {out.name}")


if __name__ == "__main__":
    main()
